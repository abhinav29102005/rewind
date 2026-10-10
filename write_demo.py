content = """# Rewind AI Presentation Demo Guide

Welcome to the live demo area! This folder is the "stage" for your presentation to the judges. It contains dummy production files (`production.db`, `important_data.csv`, `config.json`) so you can safely demonstrate Rewind intercepting a destructive AI command.

Follow this exact script to deliver a flawless pitch:

## Step 1: Set the Stage (The "Oops" Moment)
**What you do:** Show the judges this `demo/` folder and its files.
**What you say:** "Imagine I am a tired developer at 3 AM. I ask my AI coding agent to clean up the temp files, but the AI hallucinates and decides to run `rm -rf demo/` or `DROP TABLE users`, which would wipe our production database."

## Step 2: Show the Interception Effect
**What you do:** 
1. Make sure your server is running (`rewind start` in the terminal).
2. Open the Rewind Guard Dashboard in your VS Code extension.
3. Under the **"🎬 Presentation Demo Scenarios"** section, click the **Simulate: Wipe Demo Folder** button.

**What you say:** "Without Rewind, this data is gone instantly. But watch what happens with Rewind active. The AI is physically halted at the proxy layer. Notice how my IDE immediately pops up an alert? I didn't have to check a separate security portal—Rewind brought the threat directly to my workflow."

## Step 3: Show the Resolution Effect
**What you do:** Click the **"✗ Deny Action"** button in the dashboard card that just appeared.
**What you say:** "Because I denied it, the AI is cryptographically blocked from executing that payload. Our production data is completely safe."

## Step 4: Show the "Reversible" Effect (Snapshot Magic)
**What you do:** Scroll down to the **"Test Policy Classification"** box in the dashboard. Type in `chmod 777 config.json` and hit Classify.
**What you say:** "Not every action needs human approval. If an AI does something annoying but reversible—like messing up file permissions—Rewind classifies it as 'REVERSIBLE'. Instead of blocking the AI, Rewind automatically takes a shadow Git Snapshot in the background *before* the command runs. If the AI breaks the app, the developer can just click 'Rollback'."

## Step 5: The Drop-the-Mic Finish (Audit Ledger)
**What you do:** Open your terminal and run `rewind verify`.
**What you say:** "Finally, every single blocked action, approved action, and snapshot is logged in a tamper-evident, cryptographic hash chain. If an auditor asks 'Who authorized the AI to modify the database yesterday?', we have mathematical proof. We didn't just build a security tool; we built the first AI guardrail that developers will actually love using."
"""

with open("demo/DEMO_INSTRUCTIONS.md", "w") as f:
    f.write(content)
