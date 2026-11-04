# DentaVerse user survey

## Introduction

We are evaluating a proposed desktop tool for learning dental anatomy with an interactive tooth model. Participation is voluntary. You may skip questions or stop. Do not provide your name, student number, patient information, or other identifying details. Responses support coursework design improvements. Explain storage and deletion arrangements before distribution and collect the participant's agreement.

Use an anonymous response code. Record only the information needed for analysis. This file contains questions, not collected findings.

1. **Which best describes your role?** Dental student / Teaching demonstrator / Other. Optional study year.
2. **How often do you use digital tools or 3D models to study anatomy?** Never / Rarely / Sometimes / Often / Very often.
3. **How confident are you identifying teeth with FDI numbering?** 1 Not confident to 5 Very confident.
4. **Have you used hand tracking or gesture controls before?** Yes / No / Not sure.
5. **Which learning activities would be most useful?** Select all: identify a tooth / rotate and inspect / view layers / virtual instrument / review progress / save notes.
6. **Where and on what device would you use it?** Device: laptop / desktop / tablet / other. Setting: alone / classroom / laboratory / other. Allow multiple settings.
7. **What could make it difficult to use?** Select all: unclear instructions / camera setup / accidental gestures / small controls / visual complexity / discomfort / privacy / other.
8. **How important is a non-gesture way to operate key controls?** 1 Not important to 5 Extremely important.
9. **What would help when an interaction fails?** Select all: explanation / fixing instructions / undo or reset / pause and resume / help.
10. **What should remain visible during tooth inspection?** Select all: tooth number / tooth name / active tool / mode / instructions / progress.
11. **How comfortable would you feel using a camera-based learning tool where you study?** 1 Not comfortable to 5 Very comfortable. Optional comment.
12. **What one change would make the tool easier or more useful?** Open text.

## Optional post-task questions

After using the actual interface, rate 1 Strongly disagree to 5 Strongly agree: I knew what to do; I could identify the selected tooth; I knew which object would move; recovery was clear; I could pause/resume; I would use this tool to support anatomy learning. Ask: What was the most confusing moment, and why?

Keep pre-task preferences separate from post-task observations. Record whether a session used actual sensors or manual/simulated input.

## Ready-to-use local form

Open http://127.0.0.1:8000/research/survey.html after building the frontend. The anonymous form follows these 12 pre-task questions, requires consent, permits missing answers and downloads a CSV without uploading or retaining responses. Explain actual retention/deletion arrangements before inviting consent. Multi-select values use semicolons. `consented=yes` is required by `tools/analyze_survey.py`; the empty response template is not research data. Store actual files in ignored `data/research/`, then follow [the submission guide](../phase-ii-submission.md). The report aggregates actual supplied rows and leaves qualitative interpretation and design decisions for genuine critical analysis.

## Discussion-ready version

The Arabic form groups the twelve questions into three sections: background, needs/context, and controls/recovery. Study year stays inside Q1 and device/settings inside Q6. Progress counts answered questions, not individual subfields, and does not require all twelve answers. Reset clears consent as well as answers.

Open http://127.0.0.1:8000/research/survey.html?discussion=1 to expand the discussion guide. It maps questions to People, Activities, Contexts and Technologies and describes the analysis still needed. The guide is separate from participant questions and hidden when printing.

For a single file that opens in Edge or Chrome without the project server or an internet connection, run from the repository root:

```powershell
.venv/Scripts/python.exe tools/export_survey.py
```

Open `data/exports/DentaVerse-Survey.html`. It embeds the same HTML, CSS and JavaScript and includes no fonts, libraries or other external requests. Copy this one file to another computer to present or complete the survey. Regenerate it after editing the form. Generated exports and responses remain outside Git.

Use **طباعة / حفظ PDF** to print a blank questionnaire or save it as PDF. All choice options appear in print, including those normally inside select menus. This prints the questionnaire, not a submitted-response report; CSV is the response export.

This delivery has no public hosted URL or automatic collection inbox. Sites registration returned that the tool was unavailable, so no hosted Site was created. The local URL works only on the computer running DentaVerse; the standalone file can be shared as a file. Collecting actual participant responses and completing critical analysis remain separate tasks.
