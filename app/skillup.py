"""SkillUp - prototype of an Online Skill Development Platform.

The classes here mirror the UML class diagram and the operations mirror the
DFD Level-1 processes (1.0 Users, 2.0 Courses, 3.0 Enrolment & Payment,
4.0 Learning & Progress, 5.0 Assessment, 6.0 Certificates & Feedback).
In-memory storage stands in for the data stores D1-D7.
"""
from dataclasses import dataclass, field
from datetime import date
from itertools import count

PASS_MARK = 60  # percent needed to pass a quiz


class SkillUpError(Exception):
    """Raised when a business rule of the platform is violated."""


@dataclass
class User:
    uid: int
    name: str
    email: str
    role: str  # "learner" | "instructor" | "admin"


@dataclass
class Lesson:
    title: str


@dataclass
class Question:
    text: str
    options: list
    answer: int  # index of correct option


@dataclass
class Course:
    cid: int
    title: str
    instructor_id: int
    skill_tag: str
    price: float = 0.0
    prerequisite: int = None  # course id that must be completed first
    status: str = "draft"     # draft -> pending -> published
    lessons: list = field(default_factory=list)
    quiz: list = field(default_factory=list)
    ratings: list = field(default_factory=list)

    def avg_rating(self):
        return round(sum(self.ratings) / len(self.ratings), 2) if self.ratings else 0.0


@dataclass
class Enrollment:
    eid: int
    learner_id: int
    course_id: int
    state: str = "active"  # active -> completed -> certified | cancelled
    done_lessons: set = field(default_factory=set)
    best_score: int = None
    paid: float = 0.0


@dataclass
class Certificate:
    code: str
    learner_id: int
    course_id: int
    issued_on: date


class Platform:
    def __init__(self):
        self.users, self.courses, self.enrollments, self.certs = {}, {}, {}, {}
        self._uid, self._cid, self._eid = count(1), count(1), count(1)

    # ---- 1.0 Manage users -------------------------------------------------
    def register(self, name, email, role="learner"):
        if role not in ("learner", "instructor", "admin"):
            raise SkillUpError("invalid role")
        if "@" not in email or any(u.email == email for u in self.users.values()):
            raise SkillUpError("invalid or duplicate email")
        u = User(next(self._uid), name, email, role)
        self.users[u.uid] = u
        return u

    def _require(self, uid, role):
        u = self.users.get(uid)
        if not u or u.role != role:
            raise SkillUpError(f"action needs a {role}")
        return u

    # ---- 2.0 Manage courses -----------------------------------------------
    def create_course(self, instructor_id, title, skill_tag, lessons, quiz,
                      price=0.0, prerequisite=None):
        self._require(instructor_id, "instructor")
        c = Course(next(self._cid), title, instructor_id, skill_tag, price, prerequisite,
                   lessons=[Lesson(t) for t in lessons], quiz=list(quiz))
        self.courses[c.cid] = c
        return c

    def submit_for_review(self, cid):
        c = self.courses[cid]
        if not c.lessons or not c.quiz:
            raise SkillUpError("course needs lessons and a quiz")
        c.status = "pending"

    def approve_course(self, admin_id, cid):
        self._require(admin_id, "admin")
        c = self.courses[cid]
        if c.status != "pending":
            raise SkillUpError("course is not awaiting approval")
        c.status = "published"

    def search(self, keyword):
        k = keyword.lower()
        return [c for c in self.courses.values() if c.status == "published"
                and (k in c.title.lower() or k in c.skill_tag.lower())]

    def recommend(self, learner_id):
        """Published courses sharing a skill tag with the learner's courses."""
        mine = {e.course_id for e in self.enrollments.values() if e.learner_id == learner_id}
        tags = {self.courses[c].skill_tag for c in mine}
        recs = [c for c in self.courses.values() if c.status == "published"
                and c.skill_tag in tags and c.cid not in mine]
        return sorted(recs, key=lambda c: -c.avg_rating())

    # ---- 3.0 Enrolment & payment ------------------------------------------
    def enroll(self, learner_id, cid, payment=0.0):
        self._require(learner_id, "learner")
        c = self.courses.get(cid)
        if not c or c.status != "published":
            raise SkillUpError("course not available")
        if any(e.learner_id == learner_id and e.course_id == cid and e.state != "cancelled"
               for e in self.enrollments.values()):
            raise SkillUpError("already enrolled")
        if c.prerequisite and not any(
                e.learner_id == learner_id and e.course_id == c.prerequisite
                and e.state in ("completed", "certified") for e in self.enrollments.values()):
            raise SkillUpError("prerequisite not completed")
        if payment < c.price:
            raise SkillUpError("payment insufficient")
        e = Enrollment(next(self._eid), learner_id, cid, paid=c.price)
        self.enrollments[e.eid] = e
        return e

    # ---- 4.0 Learning & progress ------------------------------------------
    def complete_lesson(self, eid, index):
        e = self.enrollments[eid]
        c = self.courses[e.course_id]
        if e.state == "cancelled" or not 0 <= index < len(c.lessons):
            raise SkillUpError("invalid lesson or enrolment")
        e.done_lessons.add(index)
        self._refresh_state(e)

    def progress(self, eid):
        e = self.enrollments[eid]
        return round(100 * len(e.done_lessons) / len(self.courses[e.course_id].lessons))

    # ---- 5.0 Assessment ---------------------------------------------------
    def submit_quiz(self, eid, answers):
        e = self.enrollments[eid]
        c = self.courses[e.course_id]
        if len(answers) != len(c.quiz):
            raise SkillUpError("answer every question")
        right = sum(1 for q, a in zip(c.quiz, answers) if q.answer == a)
        score = round(100 * right / len(c.quiz))
        e.best_score = score if e.best_score is None else max(e.best_score, score)
        self._refresh_state(e)
        return score

    def _refresh_state(self, e):
        c = self.courses[e.course_id]
        if (e.state == "active" and len(e.done_lessons) == len(c.lessons)
                and (e.best_score or 0) >= PASS_MARK):
            e.state = "completed"

    # ---- 6.0 Certificates & feedback --------------------------------------
    def issue_certificate(self, eid):
        e = self.enrollments[eid]
        if e.state == "certified":
            return self.certs[e.eid]
        if e.state != "completed":
            raise SkillUpError("course not completed")
        cert = Certificate(f"SU-{e.course_id:03d}-{e.learner_id:04d}", e.learner_id,
                           e.course_id, date.today())
        self.certs[e.eid] = cert
        e.state = "certified"
        return cert

    def rate_course(self, eid, stars):
        e = self.enrollments[eid]
        if e.state not in ("completed", "certified"):
            raise SkillUpError("finish the course before rating")
        if not 1 <= stars <= 5:
            raise SkillUpError("rating must be 1-5")
        self.courses[e.course_id].ratings.append(stars)

    def instructor_report(self, instructor_id):
        self._require(instructor_id, "instructor")
        out = []
        for c in self.courses.values():
            if c.instructor_id == instructor_id:
                es = [e for e in self.enrollments.values() if e.course_id == c.cid]
                out.append({"course": c.title, "learners": len(es),
                            "completed": sum(e.state in ("completed", "certified") for e in es),
                            "revenue": sum(e.paid for e in es), "rating": c.avg_rating()})
        return out

    def cancel_enrollment(self, eid):
        e = self.enrollments[eid]
        if e.state == "certified":
            raise SkillUpError("certified enrolment cannot be cancelled")
        e.state = "cancelled"
