from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FILES=[
    ROOT/"app"/"automation.py", ROOT/"app"/"grow_alerts.py", ROOT/"app"/"maintenance.py", ROOT/"app"/"recipes.py", ROOT/"app"/"timelapse.py",
    ROOT/"web"/"platform.js", ROOT/"web"/"platform-master.js", ROOT/"web"/"final-master-live.js",
    ROOT/"web"/"menu-live.js", ROOT/"web"/"usb_onboarding.js",
]
BROKEN=(
    "?bersicht","R?ume","Ger?te","Bew?sserung","Zeitpl?ne","Bl?te","Sp?lung","D?ngung","Sch?dlinge",
    "N?hrstoffe","verf?gbar","best?tigt","ung?ltig","Ung?ltig","besch?digt","vollst?ndige","Identit?t",
    "pr?fen","Pr?fung","gel?scht","Datentr?ger","ben?tigt","au?erhalb","ausf?hrbar","ausgef?hrt","l?uft",
    "repr?sentativ","auff?llig","0?100","NICHT VERF?GBAR","N?hrstoffe","f?r","g?ltig","?ber",
)

def test_productive_ui_and_errors_have_no_known_broken_german_tokens():
    failures=[]
    for path in FILES:
        text=path.read_text(encoding="utf-8")
        for token in BROKEN:
            if token in text:
                failures.append(f"{path.relative_to(ROOT)}: {token}")
    assert not failures, "broken visible German tokens: " + ", ".join(failures)



def test_productive_ui_has_no_unicode_replacement_character():
    failures=[]
    for path in FILES:
        text=path.read_text(encoding="utf-8")
        if "\ufffd" in text:
            failures.append(str(path.relative_to(ROOT)))
    assert not failures, "Unicode replacement character in: " + ", ".join(failures)


def test_productive_ui_has_no_known_visible_question_mark_artifacts():
    bad=("? LIVE", " ?C", "NICHT VERF?GBAR", " ? Frischsubstrat ", "Vorhanden ? ", " ? Warnung")
    failures=[]
    for path in FILES:
        text=path.read_text(encoding="utf-8")
        for token in bad:
            if token in text:
                failures.append(f"{path.relative_to(ROOT)}: {token}")
    assert not failures, "visible question-mark artifacts: " + ", ".join(failures)
