"""Unit tests for the business rules (TC01-TC20)."""
import pytest
from app.skillup import Platform, Question, SkillUpError
QS = [Question("q1", ["a", "b"], 0), Question("q2", ["a", "b"], 1)]


@pytest.fixture
def world():
    p = Platform()
    admin = p.register("Admin", "a@x.com", "admin")
    inst = p.register("Inst", "i@x.com", "instructor")
    lrn = p.register("Lrn", "l@x.com")
    c = p.create_course(inst.uid, "Python", "programming", ["L1", "L2"], QS, price=100)
    p.submit_for_review(c.cid)
    p.approve_course(admin.uid, c.cid)
    return p, admin, inst, lrn, c


def test_TC01_register_valid_user():
    p = Platform()
    assert p.register("N", "n@x.com").role == "learner"


def test_TC02_duplicate_email_rejected():
    p = Platform()
    p.register("N", "n@x.com")
    with pytest.raises(SkillUpError):
        p.register("M", "n@x.com")


def test_TC03_only_instructor_creates_course(world):
    p, _, _, lrn, _ = world
    with pytest.raises(SkillUpError):
        p.create_course(lrn.uid, "X", "t", ["l"], QS)


def test_TC04_unapproved_course_not_searchable(world):
    p, _, inst, _, _ = world
    p.create_course(inst.uid, "Hidden Java", "java", ["l"], QS)
    assert p.search("java") == []


def test_TC05_search_finds_published_course(world):
    p, *_ = world
    assert [c.title for c in p.search("pyth")] == ["Python"]


def test_TC06_enroll_with_payment(world):
    p, _, _, lrn, c = world
    assert p.enroll(lrn.uid, c.cid, payment=100).state == "active"


def test_TC07_insufficient_payment_rejected(world):
    p, _, _, lrn, c = world
    with pytest.raises(SkillUpError):
        p.enroll(lrn.uid, c.cid, payment=50)


def test_TC08_duplicate_enrollment_rejected(world):
    p, _, _, lrn, c = world
    p.enroll(lrn.uid, c.cid, 100)
    with pytest.raises(SkillUpError):
        p.enroll(lrn.uid, c.cid, 100)


def test_TC09_prerequisite_enforced(world):
    p, admin, inst, lrn, c = world
    adv = p.create_course(inst.uid, "Adv", "programming", ["l"], QS, prerequisite=c.cid)
    p.submit_for_review(adv.cid)
    p.approve_course(admin.uid, adv.cid)
    with pytest.raises(SkillUpError):
        p.enroll(lrn.uid, adv.cid)


def test_TC10_progress_calculation(world):
    p, _, _, lrn, c = world
    e = p.enroll(lrn.uid, c.cid, 100)
    p.complete_lesson(e.eid, 0)
    assert p.progress(e.eid) == 50


def test_TC11_quiz_scoring(world):
    p, _, _, lrn, c = world
    e = p.enroll(lrn.uid, c.cid, 100)
    assert p.submit_quiz(e.eid, [0, 1]) == 100
    assert p.submit_quiz(e.eid, [1, 1]) == 50 and e.best_score == 100


def test_TC12_certificate_needs_completion(world):
    p, _, _, lrn, c = world
    e = p.enroll(lrn.uid, c.cid, 100)
    with pytest.raises(SkillUpError):
        p.issue_certificate(e.eid)


def test_TC13_end_to_end_certificate(world):
    p, _, _, lrn, c = world
    e = p.enroll(lrn.uid, c.cid, 100)
    p.complete_lesson(e.eid, 0); p.complete_lesson(e.eid, 1)
    p.submit_quiz(e.eid, [0, 1])
    cert = p.issue_certificate(e.eid)
    assert cert.code.startswith("SU-") and e.state == "certified"


def test_TC14_failed_quiz_blocks_completion(world):
    p, _, _, lrn, c = world
    e = p.enroll(lrn.uid, c.cid, 100)
    p.complete_lesson(e.eid, 0); p.complete_lesson(e.eid, 1)
    p.submit_quiz(e.eid, [1, 0])
    assert e.state == "active"


def test_TC15_rating_requires_completion(world):
    p, _, _, lrn, c = world
    e = p.enroll(lrn.uid, c.cid, 100)
    with pytest.raises(SkillUpError):
        p.rate_course(e.eid, 5)


def test_TC16_instructor_report(world):
    p, _, inst, lrn, c = world
    p.enroll(lrn.uid, c.cid, 100)
    r = p.instructor_report(inst.uid)[0]
    assert r["learners"] == 1 and r["revenue"] == 100


def test_TC17_recommendation_by_skill_tag(world):
    p, admin, inst, lrn, c = world
    d = p.create_course(inst.uid, "Data Structures", "programming", ["l"], QS)
    p.submit_for_review(d.cid); p.approve_course(admin.uid, d.cid)
    p.enroll(lrn.uid, c.cid, 100)
    assert [x.title for x in p.recommend(lrn.uid)] == ["Data Structures"]


def test_TC18_cancelled_enrollment_can_reenroll(world):
    p, _, _, lrn, c = world
    e = p.enroll(lrn.uid, c.cid, 100)
    p.cancel_enrollment(e.eid)
    assert p.enroll(lrn.uid, c.cid, 100).state == "active"


def _certify(p, lrn, c):
    e = p.enroll(lrn.uid, c.cid, 100)
    p.complete_lesson(e.eid, 0); p.complete_lesson(e.eid, 1)
    p.submit_quiz(e.eid, [0, 1])
    return e


def test_TC19_rating_accepted_after_completion_and_range_checked(world):
    p, _, _, lrn, c = world
    e = _certify(p, lrn, c)
    p.rate_course(e.eid, 4)
    assert c.avg_rating() == 4.0
    with pytest.raises(SkillUpError):
        p.rate_course(e.eid, 6)


def test_TC20_certificate_is_idempotent_and_blocks_cancel(world):
    p, _, _, lrn, c = world
    e = _certify(p, lrn, c)
    first = p.issue_certificate(e.eid)
    assert p.issue_certificate(e.eid) is first
    with pytest.raises(SkillUpError):
        p.cancel_enrollment(e.eid)
