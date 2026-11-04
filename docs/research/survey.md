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
