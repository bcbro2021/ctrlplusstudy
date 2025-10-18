# CTRL + STUDY

## Overview

The **CTRL+Study Tracker** is a gamified productivity application designed to help students transform their physical timetables into actionable digital study plans. By integrating vision processing (via the Gemini API) and a point-based reward system, it encourages consistent study habits and makes tracking progress engaging.

The UI is built on a modern **high-contrast, black-and-white paper style** for a clean, distraction-free experience.

## Why did we build this?

* This project was built, as a product to be showcased in an interschool hackathon hosted by Sanskara School, infopark, Kochi.

* It was made within 5 hours as a rapid prototype and is hopefully going to be worked on further by the team.

* The team consists of myself and 3 others, Sreehari, Sreeram and Nakul.

## Core Features

* **Timetable Processing:** Use an image of your physical timetable (handwritten or printed). The Gemini model processes the image to automatically extract days, subjects, and suggested study times.

* **Goal Setting:** Study time is divided equally among subjects for the day, establishing clear, achievable goals.

* **Point System:** Complete subjects to earn **"Points"** (1 point = 1 minute of scheduled study time).

* **Persistent User Progress:** Your score, completed tasks, and shop unlocks are saved uniquely based on the **username** you enter on the startup screen, allowing multiple users to track their progress separately.

* **Reward Shop:** Spend your earned Points in the **Soul Society Shop** to unlock virtual characters and rewards.

## Running the Application

### Prerequisites

To run this application, you must have the following installed:

1. **Python 3.x**

2. **PyQt5:** The framework used for the graphical user interface.

3. **Google GenAI SDK:** Required for vision processing (timetable image analysis).

### Installation & Dependencies

Install the required Python packages using pip:

```bash
  pip install PyQt5 google-genai
```

### Execution
1. api key should be provided first

2. Run main.py from your terminal

### First Time Setup

1. **Enter Username:** On the startup screen, enter a unique username. This name is used to load your previous progress or start a new session.

2. **Load Timetable:** Navigate to the Image Loader and upload a clear photo of your school or study timetable.

3. **Start Studying:** Once processed, navigate to the To-Do list, complete tasks, and earn points!

**Note on Progress:** Progress (Points, Subject Status, Unlocks) is saved to a local JSON file in a directory named `users/` under the format `[your_username]_progress.json`.