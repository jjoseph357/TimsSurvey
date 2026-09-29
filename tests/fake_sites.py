"""Local recreations of the survey sites, just faithful enough to drive the real automators.

Markup mirrors pages captured from mydqexperience.com (SMG) and telltims.ca (Qualtrics).
"""
import threading

from flask import Flask, request, session, redirect
from werkzeug.serving import make_server

SATISFACTION = [(5, "Highly Satisfied"), (4, "Satisfied"), (3, "Neither Satisfied nor Dissatisfied"),
                (2, "Dissatisfied"), (1, "Highly Dissatisfied")]
LIKELIHOOD = [(5, "Highly Likely"), (4, "Likely"), (3, "Somewhat Likely"),
              (2, "Not Very Likely"), (1, "Not At All Likely")]
YES_NO = [(1, "Yes"), (2, "No")]

# Each page is a list of questions: (kind, name, text, options). Radio questions are required.
SMG_PAGES = [
    [("matrix", "R000137", "Did you visit the Dairy Queen located at 1418 COLLEGE DR?", YES_NO)],
    [("matrix", "R000007", "Please rate your overall satisfaction with your Dairy Queen experience.", SATISFACTION)],
    [("list", "R000010", "What was your visit type?", [(2, "Carry Out"), (4, "Delivery"), (1, "Dine In")])],
    [("checkbox", "R000012", "What did you order? Check all that apply.", [(1, "Treats")])],
    [("matrix", "R000029", "The interior cleanliness of the restaurant.", SATISFACTION),
     ("matrix", "R000028", "The friendliness of the staff.", SATISFACTION),
     ("matrix", "R000017", "The taste of your order.", SATISFACTION)],
    [("matrix", "R000032", "Did you have a problem during your experience with Dairy Queen?", YES_NO)],
    [("matrix", "R000036", "Recommend this Dairy Queen to others in the next 30 days?", LIKELIHOOD),
     ("matrix", "R000035", "Return to this Dairy Queen in the next 30 days?", LIKELIHOOD)],
    [("textarea", "S000039", "Please tell us in three or more sentences why you were Highly Satisfied.", [])],
    [("list", "R000114", "Would you like to recognize a crew member?", YES_NO)],
]
PROBLEM_PAGE = [("required_textarea", "S000033", "Please describe the problem you experienced.", [])]

RADIO_JS = """
<script>
document.querySelectorAll('.inputtyperbloption, .radioButtonHolder, label.rblLabel').forEach(function(el){
  el.addEventListener('click', function(){
    var input = el.querySelector('input') || document.getElementById(el.getAttribute('for'));
    input.checked = true;
  });
});
</script>
"""


def smg_dq_validation_code(code):
    return "27" + "".join(str(ord(c) % 10) for c in code)[:8]


def _smg_page_html(page, errors):
    rows = []
    if errors:
        rows.append(f'<div class="Error">* Error: There {"is" if errors == 1 else "are"} {errors} error(s) on the page.</div>')
    for kind, name, text, options in page:
        if kind == "matrix":
            headers = "".join(f'<th id="{name}h{v}">{label}</th>' for v, label in options)
            cells = "".join(
                f'<td class="Opt{v} inputtyperbloption" aria-labelledby="text{name}" aria-describedby="{name}h{v}">'
                f'<span class="radioSimpleInput"></span>'
                f'<input type="radio" name="{name}" value="{v}" id="{name}.{v}" style="display:none"></td>'
                for v, _ in options)
            rows.append(f'<table><tr><td></td>{headers}</tr>'
                        f'<tr><th id="text{name}">{text}</th>{cells}</tr></table>')
        elif kind == "list":
            items = "".join(
                f'<div><span class="radioButtonHolder"><span class="radioSimpleInput"></span>'
                f'<input type="radio" name="{name}" value="{v}" id="{name}.{v}" style="display:none"></span>'
                f'<label class="rblLabel" for="{name}.{v}">{label}</label></div>'
                for v, label in options)
            rows.append(f'<fieldset><legend>{text}</legend>{items}</fieldset>')
        elif kind == "checkbox":
            items = "".join(
                f'<input type="checkbox" name="{name}" value="{v}" id="{name}"><label for="{name}">{label}</label>'
                for v, label in options)
            rows.append(f'<p>{text}</p>{items}')
        else:
            rows.append(f'<label for="{name}">{text}</label><textarea id="{name}" name="{name}"></textarea>')
    return (f'<html><body><form method="post" id="surveyForm">{"".join(rows)}'
            f'<input type="submit" id="NextButton" name="NextButton" value="Next"></form>{RADIO_JS}</body></html>')


def create_smg_app():
    app = Flask(__name__)
    app.secret_key = "fake"

    @app.route("/", methods=["GET"])
    def entry():
        error = '<div class="Error">Error: The survey code entered is invalid.</div>' if request.args.get("bad") else ""
        return (f'<html><body>{error}<form method="post" id="surveyEntryForm" action="/Survey.aspx">'
                f'Survey Code: <input type="text" id="CN1" name="CN1" maxlength="15">'
                f'<input type="submit" id="NextButton" name="NextButton" value="Start"></form></body></html>')

    @app.route("/Survey.aspx", methods=["POST"])
    def survey():
        if "CN1" in request.form:
            code = request.form["CN1"]
            if len(code) != 15:
                return redirect("/?bad=1")
            session["code"], session["pages"] = code, list(range(len(SMG_PAGES)))
            return _smg_page_html(SMG_PAGES[0], 0)

        remaining = session["pages"]
        page = _current(remaining)
        missing = [name for kind, name, _, _ in page
                   if kind in ("matrix", "list", "required_textarea") and not request.form.get(name, "").strip()]
        if missing:
            return _smg_page_html(page, len(missing))
        if any(name == "R000032" and request.form.get(name) == "1" for _, name, _, _ in page):
            remaining.insert(1, "problem")
        remaining.pop(0)
        session["pages"] = remaining
        if not remaining:
            return redirect("/Finish.aspx")
        return _smg_page_html(_current(remaining), 0)

    @app.route("/Finish.aspx")
    def finish():
        return ('<html><body><div id="finishIncentiveHolder"><p class="FinishHeader">Validate Your Offer</p>'
                '<p>Please write the following validation code on your receipt/coupon.</p>'
                f'<p class="ValCode">Validation Code: {smg_dq_validation_code(session["code"])}</p>'
                '<p>Offer valid only at this location. Please redeem within 30 days of your visit.</p>'
                '</div></body></html>')

    return app


# telltims.ca: a Qualtrics form in an iframe. Each page lists the answer ids it requires.
QUALTRICS_PAGES = [
    ["QR~QID14~1"], ["QR~QID15~4"], ["textarea:QR~QID45"], ["QR~QID18~5"], ["QR~QID19~5"], ["QR~QID20~5"],
    ["QR~QID23~4~1", "QR~QID23~6~1", "QR~QID23~7~1", "QR~QID23~8~1", "QR~QID23~10~1", "QR~QID23~11~1"],
    [],
    ["QR~QID151~3"], ["QR~QID44~1~1", "QR~QID44~3~1"], ["QR~QID37~2"], ["QR~QID134~2"], ["QR~QID150~2"],
    ["QR~QID48~5"], ["QR~QID68~2"],
]


def tims_validation_code(code):
    return code[-7:]


def _qualtrics_page_html(ids, error=""):
    fields = []
    for element_id in ids:
        if element_id.startswith("textarea:"):
            tid = element_id.split(":", 1)[1]
            fields.append(f'<textarea id="{tid}" name="{tid}"></textarea>')
        else:
            fields.append(f'<input type="radio" id="{element_id}" name="{element_id}" value="on">')
    intro = "<p>Is your feedback related to a recent visit?</p>" if ids == QUALTRICS_PAGES[0] else ""
    return (f'<html><body>{error}<form method="post" action="/jfe/form">{intro}{"".join(fields)}'
            f'<button id="NextButton" type="submit">Next</button></form></body></html>')


def create_qualtrics_app():
    app = Flask(__name__)
    app.secret_key = "fake"

    @app.route("/")
    def home():
        return '<html><body><h1>Tell Tims</h1><iframe src="/jfe/form" width="1000" height="700"></iframe></body></html>'

    @app.route("/jfe/form", methods=["GET"])
    def start():
        session.clear()
        return ('<html><body><form method="post" action="/jfe/form">Enter the code from your receipt'
                '<input type="text" id="QR~QID9" name="code">'
                '<button id="NextButton" type="submit">Next</button></form></body></html>')

    @app.route("/jfe/form", methods=["POST"])
    def advance():
        if "page" not in session:
            code = request.form.get("code", "")
            if len(code) != 21:
                return '<html><body><p>Invalid survey code.</p></body></html>'
            session["code"], session["page"] = code, 0
            return _qualtrics_page_html(QUALTRICS_PAGES[0])

        page = session["page"]
        required = [i for i in QUALTRICS_PAGES[page] if not i.startswith("textarea:")]
        if any(i not in request.form for i in required):
            return _qualtrics_page_html(QUALTRICS_PAGES[page], '<p class="ValidationError">Please answer.</p>')
        session["page"] = page + 1
        if page + 1 == len(QUALTRICS_PAGES):
            return ('<html><body><div class="EndOfSurvey"><p>Thank you for your feedback!</p>'
                    f'<p>Validation Code: {tims_validation_code(session["code"])}</p>'
                    '<p>Please write this code on your receipt.</p></div></body></html>')
        return _qualtrics_page_html(QUALTRICS_PAGES[page + 1])

    return app


def _current(remaining):
    return PROBLEM_PAGE if remaining[0] == "problem" else SMG_PAGES[remaining[0]]


class ServedApp:
    def __init__(self, app):
        self._server = make_server("127.0.0.1", 0, app, threaded=True)
        self.url = f"http://127.0.0.1:{self._server.server_port}/"
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def close(self):
        self._server.shutdown()
