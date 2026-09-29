"""End-to-end: the real Selenium automators against local recreations of the survey sites."""
import time

from survey_automator import make_automator
from tests.fake_sites import smg_dq_validation_code, tims_validation_code

DQ_CODE = "3BNM6JL4021TG12"


def is_png(path):
    with open(path, "rb") as f:
        return f.read(8) == b"\x89PNG\r\n\x1a\n"


def png_size(path):
    with open(path, "rb") as f:
        header = f.read(24)
    return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")


def test_dq_survey_completes_with_validation_code_and_code_image(fake_dq_site):
    automator = make_automator("dq", base_url=fake_dq_site)

    automator.start_survey(DQ_CODE)

    assert automator.status == "Completed", automator.logs
    assert automator.result_code == smg_dq_validation_code(DQ_CODE)
    assert is_png(automator.result_image_path)
    assert is_png(automator.code_image_path)
    width, height = png_size(automator.code_image_path)
    assert width < 500 and height < 150, "code image should be a tight crop, not a page-wide strip"


def test_dq_rejected_code_reports_error(fake_dq_site):
    automator = make_automator("dq", base_url=fake_dq_site)

    automator.start_survey("TOOSHORT")

    assert automator.status.startswith("Error")
    assert "rejected the code" in automator.status
    assert automator.result_code is None


def test_tims_survey_completes_with_validation_code_and_code_image(fake_tims_site):
    code = "123456789012345678901"
    automator = make_automator("tims", base_url=fake_tims_site)

    automator.start_survey(code)

    assert automator.status == "Completed", automator.logs
    assert automator.result_code == tims_validation_code(code)
    assert is_png(automator.result_image_path)
    width, height = png_size(automator.code_image_path)
    assert width < 500 and height < 150


def test_parallel_surveys_each_get_their_own_code_and_image(fake_dq_site, fake_tims_site):
    from jobs import JobManager
    urls = {"dq": fake_dq_site, "tims": fake_tims_site}
    manager = JobManager(lambda site: make_automator(site, base_url=urls[site]), max_concurrent=3)
    codes = ["AAAAAAAAAAAAAAA", "BBBBBBBBBBBBBBB", "111111111111111111111"]

    jobs = [manager.submit(c) for c in codes]
    deadline = time.time() + 60
    while time.time() < deadline and any(j.state in ("queued", "running") for j in jobs):
        time.sleep(0.1)

    assert [j.state for j in jobs] == ["done", "done", "done"], [j.automator.logs for j in jobs]
    assert [j.automator.result_code for j in jobs] == [
        smg_dq_validation_code(codes[0]), smg_dq_validation_code(codes[1]), tims_validation_code(codes[2])]
    assert len({j.automator.code_image_path for j in jobs}) == 3
