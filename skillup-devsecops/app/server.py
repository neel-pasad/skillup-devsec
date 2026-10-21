"""SkillUp web server (Flask). Wraps the tested business logic in app/skillup.py.

DevSecOps hardening in this file:
  * security headers on every response (CSP, X-Frame-Options, nosniff, ...)
  * request-size limit and input length validation
  * /health endpoint used by the Docker HEALTHCHECK and the Jenkins smoke test
  * no debug mode, no secrets in code
"""
import os
from flask import Flask, jsonify, request, send_from_directory
from app.skillup import Platform, Question, SkillUpError

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
MAX_TEXT = 120       # longest allowed name / title / tag / email
MAX_LIST = 30        # most lessons per course


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise SkillUpError(f"{field} is required")
    if len(value) > MAX_TEXT:
        raise SkillUpError(f"{field} is too long (max {MAX_TEXT} characters)")
    return value.strip()


def seed(platform):
    """Demo data: one admin, one instructor, two published courses."""
    admin = platform.register("Asha (Admin)", "asha@skillup.edu", "admin")
    meera = platform.register("Meera (Instructor)", "meera@skillup.edu", "instructor")
    quiz = [Question("Which tag marks a hyperlink?", ["<a>", "<p>", "<div>"], 0),
            Question("CSS is used for?", ["Styling", "Databases"], 0)]
    for title, tag, price, prereq in [("Web Development Basics", "web", 0, None),
                                      ("Data Structures", "programming", 999, 3)]:
        c = platform.create_course(meera.uid, title, tag, ["Introduction", "Core ideas", "Practice"],
                                   quiz, price=price, prerequisite=prereq)
        platform.submit_for_review(c.cid)
        platform.approve_course(admin.uid, c.cid)


def create_app(with_seed=True):
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
    P = Platform()
    if with_seed:
        seed(P)

    def dump():
        cs = [dict(cid=c.cid, title=c.title, tag=c.skill_tag, price=c.price, status=c.status,
                   instructor=P.users[c.instructor_id].name, instructor_id=c.instructor_id,
                   lessons=[l.title for l in c.lessons], rating=c.avg_rating(), nratings=len(c.ratings),
                   prereq=(P.courses[c.prerequisite].title if c.prerequisite in P.courses
                           else (f"course #{c.prerequisite}" if c.prerequisite else None)),
                   quiz=[dict(text=q.text, options=q.options) for q in c.quiz]) for c in P.courses.values()]
        es = [dict(eid=e.eid, learner_id=e.learner_id, cid=e.course_id, state=e.state, done=sorted(e.done_lessons),
                   score=e.best_score, progress=P.progress(e.eid),
                   cert=(P.certs[e.eid].code if e.eid in P.certs else None)) for e in P.enrollments.values()]
        return dict(users=[u.__dict__ for u in P.users.values()], courses=cs, enrollments=es)

    def do_create(b):
        lessons = b["lessons"]
        if not isinstance(lessons, list) or not 0 < len(lessons) <= MAX_LIST:
            raise SkillUpError("provide between 1 and %d lessons" % MAX_LIST)
        quiz = [Question(_text(q["text"], "question"), [_text(o, "option") for o in q["options"]], int(q["answer"]))
                for q in b["quiz"]]
        price = float(b["price"])
        if price < 0:
            raise SkillUpError("price cannot be negative")
        return P.create_course(int(b["uid"]), _text(b["title"], "title"), _text(b["tag"], "skill tag"),
                               [_text(l, "lesson") for l in lessons], quiz, price, b["prereq"]).cid

    actions = {
        "register": lambda b: P.register(_text(b["name"], "name"), _text(b["email"], "email"), b["role"]).uid,
        "create_course": do_create,
        "submit": lambda b: P.submit_for_review(int(b["cid"])),
        "approve": lambda b: P.approve_course(int(b["uid"]), int(b["cid"])),
        "enroll": lambda b: P.enroll(int(b["uid"]), int(b["cid"]), float(b["payment"])).eid,
        "lesson": lambda b: P.complete_lesson(int(b["eid"]), int(b["i"])),
        "quiz": lambda b: P.submit_quiz(int(b["eid"]), [int(a) for a in b["answers"]]),
        "cert": lambda b: P.issue_certificate(int(b["eid"])).code,
        "rate": lambda b: P.rate_course(int(b["eid"]), int(b["stars"])),
        "report": lambda b: P.instructor_report(int(b["uid"])),
    }

    @app.after_request
    def secure_headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.get("/")
    def index():
        return send_from_directory(STATIC_DIR, "index.html")

    @app.get("/health")
    def health():
        return jsonify(status="ok", users=len(P.users), courses=len(P.courses))

    @app.get("/api/state")
    def state():
        return jsonify(dump())

    @app.post("/api/<action>")
    def act(action):
        if action not in actions:
            return jsonify(ok=False, error="unknown action", state=dump()), 404
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify(ok=False, error="invalid JSON body", state=dump()), 400
        try:
            return jsonify(ok=True, result=actions[action](body), state=dump())
        except SkillUpError as e:
            return jsonify(ok=False, error=str(e), state=dump())
        except (KeyError, ValueError, TypeError, AttributeError):
            return jsonify(ok=False, error="invalid request", state=dump()), 400

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5055")))
