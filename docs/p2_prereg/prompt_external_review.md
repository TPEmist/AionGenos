# P2 External Prompt & Harness Review: Voyager, Gemini 4 Argon, and Anthropic vs. AionGenos (`WP1-③a` Push)

**Document ID**: `docs/p2_prereg/prompt_external_review.md`  
**Date**: 2026-10-28  
**Scope**: Spec Task 5 — Primary-source collection of prompt texts and harness descriptions from Voyager (`MineDojo/Voyager`), Gemini 4 Argon for Robotics, and Anthropic's *Claude plays robotics*; exact code-level reconstruction of the AionGenos `WP1-③a` push prompt pipeline; item-by-item comparative analysis against AionGenos provenance observations; and candidate prompt changes for PI decision. No code changes are made.

---

## 0. E1 Verified Primary-Source Bibliography

Every reference below was directly fetched and verified from its primary source page on 2026-10-28:

1. **Voyager (Paper & Official Repository)**
   - **Title**: *Voyager: An Open-Ended Embodied Agent with Large Language Models*
   - **Authors**: Guanzhi Wang, Yuqi Xie, Yunfan Jiang, Ajay Mandlekar, Chaowei Xiao, Yuke Zhu, Linxi Fan, Anima Anandkumar (NVIDIA, Caltech, UT Austin, Stanford, ASU)
   - **Venue / Year**: arXiv preprint `arXiv:2305.16291` (v1 submitted 25 May 2023; v2 revised 19 Oct 2023; BibTeX verified from repo `README.md`)
   - **Fetched Sources**:
     - Abstract & metadata: `https://arxiv.org/abs/2305.16291`
     - Project page: `https://voyager.minedojo.org/`
     - Repository prompts & agent code: `https://github.com/MineDojo/Voyager` (`voyager/prompts/*.txt`, `voyager/agents/*.py`, `voyager/voyager.py`, `voyager/control_primitives_context/*.js`)

2. **Gemini 4 Argon for Robotics**
   - **Title**: *Gemini 4 Argon for Robotics*
   - **Author**: Kanishka Rao (Principal Software Engineer)
   - **Venue / Date**: Google for Developers Blog, published Oct. 13, 2026
   - **Fetched Source**: `https://developers.googleblog.com/gemini-4-argon-for-robotics`

3. **Anthropic "Claude plays robotics"**
   - **Title**: *Claude plays robotics*
   - **Authors**: Shmuel Berman, Michael Ilie, Jia Deng, and Daniel Freeman (Team: Frontier Red Team)
   - **Venue / Date**: Anthropic Research, published Jul 9, 2026
   - **Fetched Source**: `https://www.anthropic.com/research/claude-plays-robotics`

---

## 1. Primary-Source Prompt Texts & Harness Specifications

### 1.1 Voyager (`MineDojo/Voyager` Repository)

#### (a) Curriculum Prompt — `voyager/prompts/curriculum.txt` (lines 1–45, verbatim)
```text
You are a helpful assistant that tells me the next immediate task to do in Minecraft. My ultimate goal is to discover as many diverse things as possible, accomplish as many diverse tasks as possible and become the best Minecraft player in the world.

I will give you the following information:
Question 1: ...
Answer: ...
Question 2: ...
Answer: ...
Question 3: ...
Answer: ...
...
Biome: ...
Time: ...
Nearby blocks: ...
Other blocks that are recently seen: ...
Nearby entities (nearest to farthest): ...
Health: Higher than 15 means I'm healthy.
Hunger: Higher than 15 means I'm not hungry.
Position: ...
Equipment: If I have better armor in my inventory, you should ask me to equip it.
Inventory (xx/36): ...
Chests: You can ask me to deposit or take items from these chests. There also might be some unknown chest, you should ask me to open and check items inside the unknown chest.
Completed tasks so far: ...
Failed tasks that are too hard: ...

You must follow the following criteria:
1) You should act as a mentor and guide me to the next task based on my current learning progress.
2) Please be very specific about what resources I need to collect, what I need to craft, or what mobs I need to kill.
3) The next task should follow a concise format, such as "Mine [quantity] [block]", "Craft [quantity] [item]", "Smelt [quantity] [item]", "Kill [quantity] [mob]", "Cook [quantity] [food]", "Equip [item]" etc. It should be a single phrase. Do not propose multiple tasks at the same time. Do not mention anything else.
4) The next task should not be too hard since I may not have the necessary resources or have learned enough skills to complete it yet.
5) The next task should be novel and interesting. I should look for rare resources, upgrade my equipment and tools using better materials, and discover new things. I should not be doing the same thing over and over again.
6) I may sometimes need to repeat some tasks if I need to collect more resources to complete more difficult tasks. Only repeat tasks if necessary.
7) Do not ask me to build or dig shelter even if it's at night. I want to explore the world and discover new things. I don't want to stay in one place.
8) Tasks that require information beyond the player's status to verify should be avoided. For instance, "Placing 4 torches" and "Dig a 2x1x2 hole" are not ideal since they require visual confirmation from the screen. All the placing, building, planting, and trading tasks should be avoided. Do not propose task starting with these keywords.

You should only respond in the format as described below:
RESPONSE FORMAT:
Reasoning: Based on the information I listed above, do reasoning about what the next task should be.
Task: The next task.

Here's an example response:
Reasoning: The inventory is empty now, chop down a tree to get some wood.
Task: Obtain a wood log.
```
- **Auxiliary curriculum prompts in repo**:
  - `voyager/prompts/curriculum_qa_step1_ask_questions.txt` (lines 1–85): asks 5–10 self-contained concept questions (`Question k: ... / Concept k: ...`) conditioned on current observation; `voyager/agents/curriculum.py:1120-1126` retrieves cached QA pairs from ChromaDB only if L2 distance `< 0.05` (`docs_and_scores[0][1] < 0.05`), and never exposes the similarity score to the LLM.
  - `voyager/prompts/curriculum_qa_step2_answer_questions.txt` (lines 1–8): answers `Question: ...` starting with `"Answer: "`.
  - `voyager/prompts/curriculum_task_decomposition.txt` (lines 1–14): decomposes `Final task: {task}` into a JSON list `["subgoal1", "subgoal2", ...]`.

#### (b) Action / Code-Generation Prompt — `voyager/prompts/action_template.txt` (lines 1–50, verbatim) & `voyager/prompts/action_response_format.txt` (lines 1–16, verbatim)
```text
You are a helpful assistant that writes Mineflayer javascript code to complete any Minecraft task specified by me.

Here are some useful programs written with Mineflayer APIs.

{programs}


At each round of conversation, I will give you
Code from the last round: ...
Execution error: ...
Chat log: ...
Biome: ...
Time: ...
Nearby blocks: ...
Nearby entities (nearest to farthest):
Health: ...
Hunger: ...
Position: ...
Equipment: ...
Inventory (xx/36): ...
Chests: ...
Task: ...
Context: ...
Critique: ...

You should then respond to me with
Explain (if applicable): Are there any steps missing in your plan? Why does the code not complete the task? What does the chat log and execution error imply?
Plan: How to complete the task step by step. You should pay attention to Inventory since it tells what you have. The task completeness check is also based on your final inventory.
Code:
    1) Write an async function taking the bot as the only argument.
    2) Reuse the above useful programs as much as possible.
        - Use `mineBlock(bot, name, count)` to collect blocks. Do not use `bot.dig` directly.
        - Use `craftItem(bot, name, count)` to craft items. Do not use `bot.craft` or `bot.recipesFor` directly.
        - Use `smeltItem(bot, name count)` to smelt items. Do not use `bot.openFurnace` directly.
        - Use `placeItem(bot, name, position)` to place blocks. Do not use `bot.placeBlock` directly.
        - Use `killMob(bot, name, timeout)` to kill mobs. Do not use `bot.attack` directly.
    3) Your function will be reused for building more complex functions. Therefore, you should make it generic and reusable. You should not make strong assumption about the inventory (as it may be changed at a later time), and therefore you should always check whether you have the required items before using them. If not, you should first collect the required items and reuse the above useful programs.
    4) Functions in the "Code from the last round" section will not be saved or executed. Do not reuse functions listed there.
    5) Anything defined outside a function will be ignored, define all your variables inside your functions.
    6) Call `bot.chat` to show the intermediate progress.
    7) Use `exploreUntil(bot, direction, maxDistance, callback)` when you cannot find something. You should frequently call this before mining blocks or killing mobs. You should select a direction at random every time instead of constantly using (1, 0, 1).
    8) `maxDistance` should always be 32 for `bot.findBlocks` and `bot.findBlock`. Do not cheat.
    9) Do not write infinite loops or recursive functions.
    10) Do not use `bot.on` or `bot.once` to register event listeners. You definitely do not need them.
    11) Name your function in a meaningful way (can infer the task from the name).

You should only respond in the format as described below:
RESPONSE FORMAT:
{response_format}
```
Where `{response_format}` (`voyager/prompts/action_response_format.txt`, lines 1–16) is:
```text
Explain: ...
Plan:
1) ...
2) ...
3) ...
...
Code:
```javascript
// helper functions (only if needed, try to avoid them)
...
// main function after the helper functions
async function yourMainFunctionName(bot) {
  // ...
}
```
```

#### (c) Skill Description & Retrieval — `voyager/prompts/skill.txt` (lines 1–10) & `voyager/agents/skill.py` (lines 103–129)
- `voyager/prompts/skill.txt` (lines 1–10, verbatim):
```text
You are a helpful assistant that writes a description of the given function written in Mineflayer javascript code.

1) Do not mention the function name.
2) Do not mention anything about `bot.chat` or helper functions.
3) There might be some helper functions before the main function, but you only need to describe the main function.
4) Try to summarize the function in no more than 6 sentences.
5) Your response should be a single line of text.
```
- **How skills are indexed and retrieved (`voyager/agents/skill.py:81-129` and `voyager/agents/action.py:76-101`)**:
  - **Write gating**: Only when `info["success"]` is `True` (`voyager/voyager.py:352-353`: `if info["success"]: self.skill_manager.add_new_skill(info)`). Failed programs are never written to the skill library.
  - **Retrieval key & presentation**: `SkillManager.retrieve_skills(query)` runs `self.vectordb.similarity_search_with_score(query, k=k)` (`k = min(count, 5)`) over the natural-language `skill_description` embeddings (`OpenAIEmbeddings()`), where `query` on round 1 is `self.context` (from curriculum QA) and on subsequent rounds is `self.context + "\n\n" + self.action_agent.summarize_chatlog(events)` (`voyager/voyager.py:187, 248-252`).
  - **Crucial detail on scores**: In `voyager/agents/skill.py:120-128`, `docs_and_scores` is unpacked as `for doc, _ in docs_and_scores: skills.append(self.skills[doc.metadata["name"]]["code"])`. **The similarity score `_` is discarded in Python and NEVER shown to the LLM.** The retrieved skill code strings are concatenated directly into `{programs}` in the system message alongside base control primitives (`voyager/agents/action.py:92`).

#### (d) Critic Prompt — `voyager/prompts/critic.txt` (lines 1–30, verbatim) & `voyager/agents/critic.py`
```text
You are an assistant that assesses my progress of playing Minecraft and provides useful guidance.

You are required to evaluate if I have met the task requirements. Exceeding the task requirements is also considered a success while failing to meet them requires you to provide critique to help me improve.

I will give you the following information:

Biome: The biome after the task execution.
Time: The current time.
Nearby blocks: The surrounding blocks. These blocks are not collected yet. However, this is useful for some placing or planting tasks.
Health: My current health.
Hunger: My current hunger level. For eating task, if my hunger level is 20.0, then I successfully ate the food.
Position: My current position.
Equipment: My final equipment. For crafting tasks, I sometimes equip the crafted item.
Inventory (xx/36): My final inventory. For mining and smelting tasks, you only need to check inventory.
Chests: If the task requires me to place items in a chest, you can find chest information here.
Task: The objective I need to accomplish.
Context: The context of the task.

You should only respond in JSON format as described below:
{
    "reasoning": "reasoning",
    "success": boolean,
    "critique": "critique",
}
Ensure the response can be parsed by Python `json.loads`, e.g.: no trailing commas, no single quotes, etc.
```
Followed in `voyager/prompts/critic.txt` (lines 32–128) by 7 concrete `INPUT:` / `RESPONSE:` few-shot examples demonstrating both `"success": true` (with `"critique": ""`) and `"success": false` (with actionable `"critique"`, e.g., `"Craft a wooden pickaxe with a crafting table using 3 spruce planks and 2 sticks."`).

---

### 1.2 Gemini 4 Argon for Robotics (`developers.googleblog.com/gemini-4-argon-for-robotics`)

#### (a) Zero-Shot Control Prompt (Axis Convention, Reticle/Grid, Turn Workflow, Primitives)
- **Anchor**: Section `Unlocking robot control with Argon` → Subsection `2. Zero-shot control`, Prompt block (verbatim):
```text
[Attached: wrist_cam.png, obs.json]

Task: Get the robot arm to reorient the mug upright and put the napkin inside the mug.

## Execution Discipline
- Simply output 1 sentence observation followed immediately by your `curl` command (with `# Plan:` on Turn 1 and `# Thought:` on every turn). Everything needed is in `obs.json` and the calibrated reticle/grid drawn on `wrist_cam.png`.

## Visual Coordinate Reference (Annotated on wrist_cam.png)
- `+X` (UP in image): Away from robot base | `-X` (DOWN): Towards robot base
- `+Y` (LEFT in image): World left         | `-Y` (RIGHT): World right
- `+Z`: Height above table                | `Yellow numbers`: World (X, Y) in centimetres (2 cm grid at `grid_z`)
- `Cyan + crosshair`: Current 3D pinch center
- `Cyan [ + ] brackets`: Current jaw opening and closing line
- `Green line`: Current object long-axis orientation (`yaw_deg`: 0° = vertical along +X, 90° = horizontal along +Y)
- `pitch_deg = 90°`: Straight down (-Z) top-down grasp/place; `pitch_deg < 60°`: Tilted coaxial approach along finger axis

## Closed-Loop Turn Workflow
1. Inspect current state & view `wrist_cam.png`:
   `curl -s http://127.0.0.1:8081/obs` (returns `ee_pos`, `holding`, `status`, `workspace`, `wrist_cam_path`).
2. Select VLM call granularity upfront on Turn 1:
   - Coarse (2–4 calls): `look_at` -> `grasp` -> `place` -> `done`
   - Pre-Grasp Hover Verify (4–7 calls): `look_at` -> `goto(z=0.04)` (verify cyan `[ + ]` brackets straddle target) -> `grasp` -> `place_until_contact` -> `done`
   - Fine Visual Servoing (8–20 calls): `look_at` -> `grasp` -> pre-pose `goto` -> closed-loop `move_by` / `move_until_contact` -> `done`
3. Send motion primitives (`POST /plan`) and verify visually after every turn in the updated `wrist_cam.png`. If `status == "grasp_failed"`, call `robot.look_at(...)` to re-observe and recover closed-loop.

## Code-as-Policies Primitives (`POST http://127.0.0.1:8081/plan`)
robot.look_at(x=0.35, y=0.13, z=0.14, grid_z=0.015)
x, y = robot.deproject(u=0.52, v=0.48, z_plane=0.015)
robot.grasp(x=x, y=y, z=0.015, yaw_deg=-35, pitch_deg=90)
robot.place(x=0.24, y=0.06, z=0.075)
robot.place_until_contact(x=0.24, y=0.06, z=0.015, max_lag=0.012, relief=0.002)
robot.goto(x=0.28, y=0.05, z=0.04, arc_z=0.14, pitch_deg=25, azimuth_deg=90, roll_deg=0, speed=0.10)
robot.move_by(forward=0.025, dz=-0.002, dpitch_deg=-3, droll_deg=5, speed=0.04)
robot.move_until_contact(dz=-0.06, speed=0.03, max_lag=0.012, relief=0.002)
robot.open_gripper() / robot.close_gripper() / robot.home() / robot.done()
```

#### (b) Other Relevant Prompts & Rules in the Argon Blog Post
- **Omni control (single-direction atomic actions & keeping inactive hands retracted)**:
  - **Anchor**: Section `Unlocking robot control with Argon` → Subsection `3. Omni control`, Prompt block (verbatim):
    > `- Break complex motions into one simple, single-direction action at a time.`  
    > `- Keep inactive hands retracted and avoid blocking the camera's view of objects in the workspace.`  
    > `- Explicitly state which areas of the workspace become empty after an object moves.`
- **Real2Sim "No sim cheating" rule**:
  - **Anchor**: Section `Unlocking Real2Sim with Argon` → Subsection `1. Robot view to simulation`, Prompt block (verbatim):
    > `No sim cheating: task objects may move only through real MuJoCo contact with the robot hands and the environment (mj_step).`  
    > `Not allowed after t = 0: changing MjModel parameters; applying external forces or torques to objects; welds or equality constraints; feedforward torques beyond joint-space PD; setting or rolling back object qpos/qvel; disabling or excluding collisions; reporting contact forces that don't come from the MuJoCo solver (for example, copying the logged tactile readings).`
- **Action improvement via simulation (Sim → VLA fine-tuning)**:
  - **Anchor**: Section `Unlocking research and self-improvement with Argon` → Subsection `1. Action improvement via simulation`, para 1 & Prompt block (verbatim):
    > `"Starting from a single RGB photo of the real tabletop, Argon autonomously builds a calibrated MuJoCo simulation twin, defines new tasks, and synthesizes a closed-loop motion generator to collect 4,500+ domain-randomized episodes in simulation—boosting real-world physical robot Success Rate from 56% to 75% and reducing completion time from 35s to 24s ."`  
    > `"3. Synthesize a closed-loop IK trajectory generator across ±10 cm pose randomization, verify reward == 1.0 in MuJoCo physics, and export 4,500+ episodes for VLA fine-tuning."`
- **Self-improvement for visual pick and place (3-stage dry-run → hover-verify → self-diagnose loop)**:
  - **Anchor**: Section `Unlocking research and self-improvement with Argon` → Subsection `2. Self-Improvement for visual pick and place`, Prompt block (verbatim):
    > `# Stage 1 — Measure Objects & Dry-Run Plan (No Hardware Motion)`  
    > `Stage 1: measure objects — find the objects and plan the whole motion. The arm does not move in this stage.`  
    > `...`  
    > `# Stage 2 — Pre-Pick Hover & Wrist-Camera Verification`  
    > `Stage 2: Put the gripper above the brick without touching it, and verify with the wrist camera that the arm and the vision agree. Please record executions with both cameras (compressed video is OK).`  
    > `# Stage 3 (Autonomous Pick-and-Place → Self-Improvement → Optimization):`  
    > `1. Execute autonomously: Turn the Stage 1 dry run into a real grasp, lift, and place into the wooden box. Run it yourself subject to safety rules from AGENTS.md.`  
    > `2. Self-improve: When an attempt fails, diagnose it yourself. Review your own logs and wrist/overhead footage, find the root cause, check the fix in a dry run, and retry.`  
    > `3. Optimize on feedback: Once it succeeds, make it at least 2× faster within safety limits (rule R5) unless I authorize more, or give feedback.`

---

### 1.3 Anthropic "Claude plays robotics" (`anthropic.com/research/claude-plays-robotics`)

Note: Full verbatim prompt strings are not published in the blog post (`NOT FOUND` verbatim; the post states in `§07 Appendix -> Reproducibility`, para 1: `"The code, once released, will be in github.com/safety-research/embody , the public mirror of the repository"`). Below are the verbatim official descriptions of the prompt template and harness mechanisms with section and paragraph anchors:

1. **Fixed Prompt Template & Embodied Details**:
   - **Anchor**: `§07 Appendix` → `Prompts`, para 1 (verbatim):
     > `"We did not tune prompts separately for each model. Each interface used one fixed prompt template. At trial time, the template was filled with task-specific details such as joint count, robot mass, force limits, and observation fields."`
2. **Low-Level Manipulation Observation & Action Interface (No Object Coordinates)**:
   - **Anchor**: `§03 Direct control is bad, but improving` → `Low-level manipulation`, para 4 (verbatim):
     > `"We test a simplified direct-control setting in which the model outputs standard seven-dimensional end-effector motion commands. After every movement, it receives images of the scene along with readings from the gripper’s force sensors, similar to what a VLA would receive. It is never given the objects’ coordinates directly, so it must first identify the relevant objects from vision and then use that information to decide how the hand should move next."`
3. **Visual & Perceptual Aids (`cursor`, `compass`, `depth`, `segmentation`, `third_person`, `ask_vlm`)**:
   - **Anchor**: `§04 Tools bridge some of the gap` → `High-level locomotion`, para 5 (verbatim):
     > `"We tested several tools to attempt to assist the model with visual and directional understanding, and more generally perception. We tried giving the model a green center crosshair drawn on its egocentric view, a semi-transparent depth heatmap alpha-blended over its view, a third-person chase camera replacing the forward view, and a "compass" which just gives the model its orientation in degrees. The compass tool handily beats the other ones, as will be elaborated upon later when we examine bottlenecks."`
   - **Anchor**: `§05 What’s the bottleneck?` → `Is visual perception the bottleneck?`, para 1, 5, 6 (verbatim):
     > `"In both manipulation and locomotion we tested whether additional visual inputs improve performance. For the Panda arm we added depth maps, labeled segmentation overlays, and a cursor tool—a small red X on the gripper cam that the model can move and query for the object and distance at that point."`  
     > `"The cursor tool, by contrast, gives every model a large uplift on manipulation—for Mythos Preview, success on the 10-task subset goes from 6% to 32%. The compass does the same for locomotion, lifting every configuration we tested. In both cases the results suggest that models mainly need better orientation, not a different view of the scene: it is still more helpful to tell the model which way it is facing than to show it a picture of itself."`  
     > `"We also tested how much information an actual image provides over a detailed textual description. To do this, we replaced the visual input with text descriptions produced by the strongest image-question-answering model we tested, Gemini 3.1."`
   - **Anchor**: `§07 Appendix` → `Vision tools`, para 1–2 (verbatim):
     > `"We also tested several ways of changing what visual information the model received:`  
     > `- --vision-depth : adds a depth heatmap overlay`  
     > `- --tools segmentation : adds a labeled segmentation map`  
     > `- --crosshair --gripper-cam : adds an interactive cursor (formerly called crosshair) on the gripper camera`  
     > `- --vision-mode ask_vlm : replaces pixels with natural-language scene descriptions from Gemini 3.1 Pro Preview`  
     > `For the high-level locomotion suite, we tested five perceptual-aid conditions in addition to the baseline forward camera:`  
     > `- compass : the robot's world-frame heading in degrees, appended as text alongside each frame`  
     > `- crosshair : a green center crosshair drawn on the forward camera image`  
     > `- depth : a semi-transparent depth heatmap alpha-blended over the forward camera image`  
     > `- third_person : the forward camera is replaced with a third-person chase camera positioned behind and above the robot`  
     > `- combo : all four aids applied together"`
4. **Adaptation After Prior Outcomes**:
   - **Anchor**: `§02 Simple settings`, para 9 (verbatim):
     > `"Our results suggest that much of the improvement comes from a better ability to adapt after seeing prior outcomes and to revise strategy accordingly. On tasks with a natural termination point (most notably TwinFlipper and Pendulum), average first-try performance is quite similar across models, and Claude Opus 4 and Opus 4.1 very slightly outperform later models on this measure. The larger gains appear in subsequent attempts, where later models improve much more substantially."`
   - **Anchor**: `§05 What’s the bottleneck?` → `Can they learn from experience?`, para 3 (verbatim):
     > `"Later Claude models do not pull ahead by starting much stronger—nearly all first attempts perform poorly, with only a few exceptions. Instead, they improve by in-context learning from failed attempts and performing better control. Opus 4.5 and Opus 4.6 benefit much more from iteration than Opus 4 and Opus 4.1. Newer versions of Claude are better able to learn from failed attempts, revise their approach, and find working solutions."`
5. **Context Truncation Rule & Keeping Prior Frames**:
   - **Anchor**: `§05 What’s the bottleneck?` → `Can they learn from experience?`, para 5–7 (verbatim):
     > `"We examine this with context-truncation experiments in manipulation, where we deliberately remove most of the prior interaction and leave the model only a much smaller window of recent actions and observations. If performance depended on a detailed memory of the full episode, this should have caused a large drop. In most cases, it did not. In some cases, performance even improved. This indicates that the models rely much more on the recent past than on a broad accumulated understanding of everything that happened earlier."`  
     > `"In these truncation runs we always retain the first 10 turns plus the most recent N turns. Dropping the first turn caused models to forget basic conventions and loop, so we keep it in all conditions."`  
     > `"Weaker models may get confused by earlier context in a documented phenomenon known as “context rot,” which explains why performance increases when context is truncated. These models were unable to learn from the distant past, so its removal is a performance enhancer."`
   - **Anchor**: `§07 Appendix` → `Vision inputs` → `Keeping prior frames`, para 1 (verbatim):
     > `"All published vision cells kept prior frames in context. This was required for Claude Agent SDK runs with vision, because that SDK path did not support deleting older images turn by turn."`
6. **Simulator Pausing**:
   - **Anchor**: `§02 Simple settings`, para 4 (verbatim):
     > `"To approximate an upper bound on direct-control performance, we pause the simulator between LLM calls so real-time latency does not dominate the results. Without this, many direct tests would fail for a trivial reason: the models would simply react too slowly to control the environment."`
   - **Anchor**: `§08 Latency`, para 5–6 (verbatim):
     > `"For direct-control and code-control simulations, we paused the simulator while the model produced its next action. Without pausing, current API models would fail for a trivial reason: they act far too slowly for a physics loop running at 10–125 Hz. Pausing lets us measure what the model could do if inference were faster, rather than only measuring today’s API latency."`  
     > `"The robot arm did not require the same tight real-time stability as locomotion, so we did not pause the simulator between model calls in the manipulation setting."`
7. **Reasoning Budget**:
   - **Anchor**: `§05 What’s the bottleneck?` → `Does reasoning help?`, para 1, 2, 5 (verbatim):
     > `"Reasoning had little effect on most of our results, with many differences falling within standard error."`  
     > `"On the classic control tasks, newer models regressed when given a higher reasoning budget. This could be due to overengineering what are relatively simple experiments."`  
     > `"On direct and high-level manipulation, reasoning made no major difference for any of the Claude-family models, although it affected Gemini 3.1 and GPT-5.4 significantly. Looking at the results across models, extra reasoning seems to hurt."`
8. **Cross-Episode / Practice Run Limits (`oneshot_course`)**:
   - **Anchor**: `§05 What’s the bottleneck?` → `Can they learn from experience?`, para 10–12 (verbatim):
     > `"When we give the models a few practice runs on the same course, performance improves across the board. ..."`  
     > `"On harder, longer courses, practice does not help. On those trials, neither Mythos Preview nor Opus 4.7 completes a single trial even with twenty practice runs. The models are learning a specific sequence and are not yet general planners."`

---

## 2. Reconstruction of AionGenos Current Prompt Pipeline from Code

### 2.1 System Prompt (`STAGE1_SYSTEM`)
From `aiongenos/vlm/prompts.py:42-49` (returned by `get_stage1_system_prompt()` at `prompts.py:480-481`, called by `run_stage1_eef` at `aiongenos/pipeline/stage1_reasoning.py:240` and `push_collect.py:305, 308`):
```text
You are a bimanual robot controller. You receive a camera image of the scene and must plan the next sub-goal for both arms.
Rules:
- All coordinates are integers in [-100, 100].
- Never output floating point numbers for coordinates.
- Reason step-by-step about the physics before giving targets.
- Output your response in the EXACT format specified below.
```
- **Delivery mechanism (`aiongenos/vlm/client.py:53-63, 152-155`)**: Because Gemma-4 / `llama.cpp` vision token injection requires system text and images to be co-located in the user turn, `STAGE1_SYSTEM + "\n\n"` is prepended as the first `{"type": "text"}` block inside the **first** `"role": "user"` message (Turn 0), rather than sent as a separate `"role": "system"` message.

### 2.2 Stage-1 Push User Prompt (`_S1_EEF_PUSH` + Dynamic Blocks)
From `aiongenos/vlm/prompts.py:147-172` (`ControlMode.PUSH_WAYPOINT` maps to `_S1_EEF_PUSH` at `prompts.py:181`):
```text
TASK: {instruction}
CONTROL_MODE: left_eef_waypoint_ori_optional

CURRENT STATE (proprioception, base-frame integers, same grid as your output):
  LEFT_EE_POS  = (X={left_x}, Y={left_y}, Z={left_z})   # left fingertip (TCP)
  RIGHT_EE_POS = (X={right_x}, Y={right_y}, Z={right_z})
  LEFT_GRIPPER = {left_gripper}
{frame_block}{oracle_block}{view_block}
The yellow cube and the green zone (flat green disc on the table) are seen in
the image; their positions are not given as numbers.
AFFORDANCE CONTRACT: the cube must end up on the green zone, moved BY PUSHING.
The gripper is held CLOSED for the entire task and CANNOT open, close, grasp,
or lift. Your ONLY action each round is one left end-effector target: a
fingertip (TCP) position (REQUIRED) and an optional orientation offset. The
next round shows the new image and state.

ORIENTATION (OPTIONAL) — LEFT_TARGET_ORI: integer degrees rotating the hand's
REST orientation about FIXED BASE-frame axes, applied as Rz(Y)·Ry(P)·Rx(R):
  P = about the base Y axis
  Y = about the base Z axis (vertical)
  R = about the base X axis
  Signs follow the right-hand rule about the positive axis. Omitted → rest
  orientation.

THOUGHT: <one paragraph physics reasoning>
LEFT_TARGET_POS: X=<int> Y=<int> Z=<int>        (required; fingertip/TCP, base-frame integers on the SAME grid as CURRENT STATE — not cm)
LEFT_TARGET_ORI: P=<int> Y=<int> R=<int>        (OPTIONAL; integer degrees about base axes, applied to the rest orientation; omit for rest)
STOP: <true|false>
```

#### Placeholder values filled at runtime:
1. **`{instruction}`** (`scripts/run_push_collect.py:164`, `aiongenos/orchestrator/push_collect.py:283`):
   `Push the yellow cube onto the green zone on the table.`
2. **`{left_x}, {left_y}, {left_z}`** (`aiongenos/orchestrator/isaaclab_env_interface.py:463-475`):
   Left fingertip (TCP) base-frame position mapped to `[-100, 100]` integer grid via `position_metric_to_int`. At reset (Pin-7a standby), `LEFT_EE_POS` is approximately `(X=-40, Y=26, Z=53)`.
3. **`{right_x}, {right_y}, {right_z}`** (`aiongenos/orchestrator/isaaclab_env_interface.py:196-198`):
   Right hand (`right_body_idx`, not TCP) world-to-grid position populated by `get_state` before `_push_state` updates the dict, even though the right arm is held still in `WP1-③a`.
4. **`{left_gripper}`** (`isaaclab_env_interface.py:476`):
   `closed (locked)`
5. **`{frame_block}`** (`d1`, enabled when `--frame_convention` is passed; `aiongenos/vlm/prompts.py:394-411`, `isaaclab_env_interface.py:471-474`):
   With default `WorkspaceBounds(x_bounds=(-0.3, 0.6), y_bounds=(-0.4, 0.4), z_bounds=(0.0, 0.7))` (`aiongenos/config.py:43-45`) and `grid_span = 200`, `format_frame_convention_line(bounds) + "\n"` renders as:
   ```text
   FRAME (base frame, same grid as the numbers above): +X = forward, away from the robot base; +Y = the robot's left; +Z = up. One grid unit = 0.45 cm in X, 0.40 cm in Y, 0.35 cm in Z.
   ```
   (Empty string `""` when `frame_convention=False`.)
6. **`{oracle_block}`** (`isaaclab_env_interface.py:479-500`):
   - At `obs_rung` `"1"` or `"1b"` (`oracle_level == 1`): `""` (empty).
   - At `obs_rung` `"2"` (`oracle_level == 2`):
     ```text
     SCAFFOLD (oracle-measured, disclosed):
       LEFT_TIP_TO_CUBE = {tip_cube * 100:.1f} cm
       CUBE_TO_GOAL     = {cube_goal * 100:.1f} cm
     ```
   - At `obs_rung` `"3"` (`oracle_level == 3`): appends `CUBE_POS`, `GOAL_POS`, `TIP_TO_CUBE`, and `CUBE_TO_GOAL` grid coordinates/deltas (note: while `_oracle_block` reveals coordinates at rung 3, the subsequent static line in `_S1_EEF_PUSH` still says `"their positions are not given as numbers"`).
7. **`{view_block}`** (`aiongenos/orchestrator/push_memory.py:61, 93-96`):
   - At `obs_rung == "1"`: `""` (empty).
   - At `obs_rung` in `{"1b", "2", "3"}`: `"The last image is a top-down view of the current scene.\n"`

### 2.3 Cross-Episode Memory Preamble (`format_push_preamble_text`)
From `aiongenos/orchestrator/push_memory.py:564-638`:
- **Retrieval scoring (`aiongenos/memory/recap_buffer.py:167-277`, `push_memory.py:64-68, 668-700`)**:
  - `score = 0.4 * img_cos + 0.6 * exp(-||query_init_L_EE - rec_init_L_EE|| / 30.0)`
  - Because `init_L_EE` is the reset-time standby TCP grid (`(-40, 26, 53)`), `||Δ init_L_EE|| ≈ 0`, so `state_sim ≈ 1.000` for every candidate. With DINOv2 cosine similarity on same-scene tabletop images `≈ 0.90–0.99`, every retrieved episode displays `(similarity=0.9xx)` (typically `0.960–0.998`).
  - `success_floor_frac = 2/3` with `top_k = 3` guarantees that up to `ceil(2/3 * 3) = 2` slots are reserved for `is_success == True` records regardless of whether failures had higher visual similarity (`recap_buffer.py:244-256`).
- **When `preamble_coords == "on"` (`push_memory.py:568-572, 601-637`)**:
  ```text
  PAST SIMILAR PUSH EPISODES (image-anchored memory). For each one you can see the scene at its start, your round-1 fingertip (TCP) target, the outcome, and a short lesson you wrote afterwards. Use these to choose a better target for the current scene.


  [PAST EPISODE 1] (similarity=0.985)
    Image 1: the scene at the start of that episode
    start TCP  = (X=-40, Y=26, Z=53)
    round-1 target = (X=60, Y=10, Z=53) ORI rest → TCP reached (X=59, Y=10, Z=53)
    outcome    = success
    rounds     = 3
    lesson     : <rec.text_lesson>
  ...
  ─── END OF PAST EPISODES ───

  The LAST image below is the CURRENT scene you must act on. Use the past lessons above to choose your target for this current scene.
  ```
  *(At `obs_rung` `1b`/`2`/`3`, `"The LAST image below is..."` becomes `"The LAST TWO images below are the CURRENT scene you must act on: front view, then top-down view."` At `obs_rung >= 2`, `cube→goal = ... cm at start, ... cm at end (disclosed)` and `(class: ...)` are also shown.)*
- **When `preamble_coords == "off"` (`push_memory.py:575-579, 606-630`)**:
  - Header omits `"your round-1 fingertip (TCP) target"`:
    ```text
    PAST SIMILAR PUSH EPISODES (image-anchored memory). For each one you can see the scene at its start, the outcome, and a short lesson you wrote afterwards. Use these to choose a better target for the current scene.
    ```
  - `start TCP`, `round-1 target`, and `cube start / goal` lines are omitted.
  - Any coordinate match in `rec.text_lesson` matching `COORD_PATTERN = re.compile(r"[XYZxyz]\s*=\s*-?\d+|\(\s*-?\d+\s*,\s*-?\d+\s*(?:,\s*-?\d+\s*)?\)")` is replaced at render time with `"[coordinates omitted]"`.

### 2.4 Per-Round Feedback (`push_feedback.py` & `prompts.py`)
On Round $r \ge 2$ when `--round_feedback` is active (`push_collect.py:272-280`, `stage1_reasoning.py:242-243`), the user prompt appends `\n\n### CRITIC FEEDBACK FROM PREVIOUS ROUND:\n` followed by `format_round_feedback(...)` (`aiongenos/orchestrator/push_feedback.py:29-66`, importing templates from `aiongenos/vlm/prompts.py:355-391`):

- **At `obs_rung` `"1"` or `"1b"` (`fb_scalars = False`, `scalars_start_cm = None`)**:
  ```text
  ### CRITIC FEEDBACK FROM PREVIOUS ROUND:
  DIAGNOSTIC REPORT FOR PREVIOUS ROUND:
    LEFT ARM:
      Target coordinate was predicted at: X={px} Y={py} Z={pz}
      Actual movement: from X={sx} Y={sy} Z={sz} to X={ex} Y={ey} Z={ez}
  ```
  **Note**: There are **no distance lines** and **no progress/regression/flat verdict line** at `obs_rung < 2`, even when `--verdict_contact_switch` (`d2`) is passed on the CLI (`push_collect.py:178, 274-280`; `push_feedback.py:15, 49-55`).
- **At `obs_rung >= 2` (`fb_scalars = True`)**:
  ```text
  ### CRITIC FEEDBACK FROM PREVIOUS ROUND:
  DIAGNOSTIC REPORT FOR PREVIOUS ROUND:
    LEFT ARM:
      Target coordinate was predicted at: X={px} Y={py} Z={pz}
      Actual movement: from X={sx} Y={sy} Z={sz} to X={ex} Y={ey} Z={sz}
      Fingertip-to-cube distance: started at {tip_start:.1f} cm, ended at {tip_end:.1f} cm
      Cube-to-goal distance: started at {cg_start:.1f} cm, ended at {cg_end:.1f} cm
      Result: <Progress / Regression / No significant progress verdict on tip_cube (before contact if d2) or cube_goal>
  ```

### 2.5 Multi-Turn Conversation Window & Image Stripping (`EpisodeConversation`)
From `aiongenos/vlm/client.py:92-182` and `aiongenos/pipeline/stage1_reasoning.py:247-260`:
- **Round 1 (`round_idx == 0`)**:
  `conversation.messages` contains a single `"role": "user"` turn whose `content` list is ordered:
  1. `{"type": "text", "text": STAGE1_SYSTEM + "\n\n"}`
  2. `{"type": "text", "text": preamble_text + "\n"}` *(if memory retrieved)*
  3. `{"type": "image_url", ...}` × $K$ *(past episode start images, $K \le 3$)*
  4. `{"type": "image_url", ...}` *(current Round-1 front camera RGB)*
  5. `{"type": "image_url", ...}` *(current Round-1 top camera RGB, if `obs_rung` in `1b/2/3`)*
  6. `{"type": "text", "text": user_prompt}` *(Round-1 `_S1_EEF_PUSH`)*
- **Round $r \ge 2$ (`round_idx >= 1`, `--round_history` on)**:
  When `append_user_turn` is called at the start of Round $r$ (`client.py:147-150`):
  ```python
  for msg in self.messages:
      if msg["role"] == "user" and isinstance(msg["content"], list):
          msg["content"] = [part for part in msg["content"] if part["type"] == "text"]
  ```
  - **Every image in all prior turns — including all $K$ retrieved memory start images AND the Round-1 scene image in Turn 0 — is stripped.**
  - Turn 0 retains only its text blocks (`STAGE1_SYSTEM`, `preamble_text` which still claims `"For each one you can see the scene at its start"`, and Round-1 `user_prompt`).
  - After each round's assistant response is appended, `_prune_to_window()` (`client.py:116-130`) retains `self.messages[0]` (Turn 0 user message) + the last `2 * DEFAULT_RECENT_WINDOW = 12` messages (last 6 user/assistant pairs). Note: when pruning triggers (from Round 8 onwards), `self.messages[0]` (user) is followed immediately by `tail[0]` (also `"role": "user"`), because Round 1's assistant response (`self.messages[1]`) is dropped while `self.messages[0]` is kept.

---

## 3. Item-by-Item Comparative Analysis: Them vs. Us vs. Provenance Observations

### 3.1 MUST-CHECK (1): Identity Framing & Embodiment Specification

- **Them**:
  - **Voyager**: Single-agent Mineflayer bot identity (`voyager/prompts/action_template.txt:1, 30`: `"writes Mineflayer javascript code to complete any Minecraft task... Write an async function taking the bot as the only argument"`). Only active state channels exist; early-stage observations are even masked via `default_warmup` (`voyager/agents/curriculum.py:821-838`, `optional_inventory_items`) so unused/distractor fields are not shown until needed.
  - **Gemini 4 Argon**: Matches the exact active embodiment per prompt. In `§2 Zero-shot control`, the prompt specifies `"Task: Get the robot arm to reorient the mug..."` and `/obs` returns only the single arm's `ee_pos`. When a bimanual or multi-limb embodiment has an inactive limb (`§3 Omni control`, Prompt bullet 2), it explicitly instructs: `"Keep inactive hands retracted and avoid blocking the camera's view of objects in the workspace."`
  - **Anthropic**: `§07 Appendix -> Prompts`, para 1: `"Each interface used one fixed prompt template. At trial time, the template was filled with task-specific details such as joint count, robot mass, force limits, and observation fields."` For LIBERO manipulation (`§03 Low-level manipulation`, para 1 & 4), the model controls a single 7-DoF Franka Panda arm and receives only that arm's 7D action space and sensors.
- **Us (AionGenos)**:
  - `STAGE1_SYSTEM` (`aiongenos/vlm/prompts.py:42-43`) says: `"You are a bimanual robot controller. You receive a camera image of the scene and must plan the next sub-goal for both arms."`
  - `_S1_EEF_PUSH` (`aiongenos/vlm/prompts.py:150-151`) prints `RIGHT_EE_POS = (X={right_x}, Y={right_y}, Z={right_z})` in `CURRENT STATE` every round, even though `WP1-③a` push is strictly a single-arm (left-arm) task where the right arm is parked and frozen (`CONTROL_MODE: left_eef_waypoint_ori_optional`, `Your ONLY action each round is one left end-effector target`).
  - Notably, in P1 `L0a` (`aiongenos/vlm/task_instructions.py:18-20`), the task instruction explicitly resolved this contradiction: `"Move your LEFT end-effector to the {target_color} target. Your right arm is held still — you do not control it."` In `WP1-③a` push (`scripts/run_push_collect.py:164`), the instruction is just `"Push the yellow cube onto the green zone on the table."`, leaving `STAGE1_SYSTEM`'s `"plan the next sub-goal for both arms"` and `RIGHT_EE_POS` uncontradicted until the affordance contract paragraph.
- **Could the difference explain an observation of ours?**
  - **Explicitly flagged in diagnosis**: `docs/p2_prereg/wp3a_rung2p_diagnosis_2026-10-22.md` §1a (line 32) notes as one of the four code differences from P1: `"that the system prompt says 'bimanual … both arms'"`.
  - **Effect on format violations vs. spatial distraction**: It does **not** cause dual-arm output format violations in `WP1-③a` because `_S1_EEF_PUSH` ends with only `LEFT_TARGET_POS` / `LEFT_TARGET_ORI` slots (0 dual-arm schema failures in `71134939`, `611a3e2a`, `663c049a`, `3786f4e5`). However, `[speculative]` printing `RIGHT_EE_POS` alongside `LEFT_EE_POS` in `CURRENT STATE` while the right arm is visible in the oblique front camera image introduces a second 3D coordinate anchor in the state block and visual scene that has zero control relevance, adding distractor tokens to Turn 0 and every subsequent round.

---

### 3.2 MUST-CHECK (2): Memory Preamble Presentation (Scores, Image Stripping, Coordinate Copying)

- **Them**:
  - **Voyager**:
    - **Scores**: Computed internally via ChromaDB (`voyager/agents/skill.py:120`, `voyager/agents/curriculum.py:1121`), **never shown to the LLM** (`for doc, _ in docs_and_scores:`).
    - **Images**: None (text/code only).
    - **Which turn**: Retrieved skills are re-queried and injected into the `SystemMessage` (`{programs}`) on **every round** of the rollout (`voyager/voyager.py:187, 248-253`).
    - **Content**: Executable, parameterized JavaScript functions (`async function mineCobblestone(bot) { ... }`), never raw past episode coordinates.
  - **Gemini 4 Argon**:
    - Does not use an episodic retrieval preamble in the prompt (`NOT FOUND` in blog post). Cross-episode improvement is either consolidated into VLA weights (`4,500+ domain-randomized episodes in simulation`, `§ Unlocking research and self-improvement -> 1. Action improvement via simulation`) or executed via within-session self-reflection over logs/video (`§ 2. Self-Improvement for visual pick and place`, Stage 3).
  - **Anthropic**:
    - No cross-episode retrieval database or similarity scores (`NOT FOUND`). In `oneshot_course` (`§05 Can they learn from experience?`, para 10–12), prior practice runs are kept in-context as prior attempts. In vision cells (`§07 Appendix -> Vision inputs -> Keeping prior frames`, para 1), `"All published vision cells kept prior frames in context."`
- **Us (AionGenos)**:
  - **Scores shown verbatim**: `format_push_preamble_text` (`aiongenos/orchestrator/push_memory.py:604`) prints `[PAST EPISODE i] (similarity=0.9xx)` for each of the top-3 records. Because `state_sim` (`weight = 0.6`) is computed on `init_L_EE` (`push_memory.py:63-66`, `recap_buffer.py:217-237`), which is always the fixed Pin-7a standby pose `(-40, 26, 53)`, `state_sim = 1.0` for all episodes, compressing all displayed similarity scores into `~0.96–0.99` even when the cube and goal are in completely different positions (`±75°` in Pin-4c).
  - **Past start images stripped from Round 2**: On Round 1, `preamble_image_base64_list` attaches the 3 past start images (`aiongenos/vlm/client.py:160-165`). At the start of Round 2 (`client.py:148-150`), `append_user_turn` strips **all** `image_url` blocks from Turn 0, leaving only the text of `preamble_text` in Turn 0 (`"PAST SIMILAR PUSH EPISODES (image-anchored memory). For each one you can see the scene at its start..."` + `"Image 1: the scene at the start of that episode"`), which now points to nonexistent images.
  - **Past coordinates (`preamble_coords="on"` vs `"off"`)**: With `preamble_coords="on"`, each retrieved block displays `start TCP = (X=-40, Y=26, Z=53)` and `round-1 target = (X=..., Y=..., Z=...) ORI ... → TCP reached (X=..., Y=..., Z=...)` (`push_memory.py:607-612`), and the `2/3` success floor (`recap_buffer.py:244`) forces any single lucky success into the top-3 preamble of all subsequent episodes.
- **Could the difference explain an observation of ours?**
  - **YES — directly explains the `(e)` coordinate-copying collapse and height-locking across episodes**:
    1. **Path copying vs. perception (`wp3a_push_provenance.md` § "2026-10-22 — rung-1′ on the d1+d2 interface: 11/50", lines 2382–2388; § "2026-10-27 — rung-1′ on Pin-4c, and the (e) two-arm result", lines 2463–2476)**:
       - In `611a3e2a` (Pin-4b, `coords="on"`), after the first success at seed 5009 (`[40,20,50]`), **35/40 subsequent episodes** emitted `[40,20,50]` as their Round-1 target ($\rho_X = +0.11$, situation-independent blind sweep).
       - In `663c049a` (Pin-4c `±75°`, `coords="on"`), after a single lucky success at seed 5001 (`[60,10,53]`), **37/49 subsequent Round-1 targets were verbatim preamble copies**, yielding only **10 unique Round-1 targets**, **161/183 rounds stuck at `Z=53`** (`1/183` in contact band), and **SR = 3/50 (6%)**.
       - In `3786f4e5` (Pin-4c `±75°`, `coords="off"`, where past coordinate lines and lesson coordinates were redacted), unique Round-1 targets jumped from **10 → 42**, `Z=53` rounds dropped from **161/183 (88%) → 37/150 (25%)**, contact-band rounds rose from **1/183 → 55/150**, $\rho_Y$ rose to **$+0.278$ ($p = 0.026$)**, and SR quadrupled from **3/50 → 13/50** (Fisher two-sided $p = 0.012$).
    2. **Why our preamble induced copying (`[speculative]` mechanism grounded in code + `(e)` data)**: Showing a falsely high `(similarity=0.98x)` badge alongside an explicit `round-1 target = (X=60, Y=10, Z=53)` and `outcome = success` tells the VLM that the retrieved episode is a 98%+ match to the current scene and hands it a ready-made integer tuple in the exact output format. Furthermore, on Round 2+, stripping the past start images (`client.py:148-150`) while keeping the text in Turn 0 removes the only visual evidence that the past episode had a different cube/goal layout (`wp3a_rung2p_diagnosis_2026-10-22.md` §1a, §2.4).

---

### 3.3 MUST-CHECK (3): Feedback Form & Outcome Verification

- **Them**:
  - **Voyager**:
    - Every step provides three structured feedback channels in `voyager/agents/action.py:440-500`:
      1. `Execution error:` runtime JS exception stack trace or `"No error"`.
      2. `Chat log:` intermediate `bot.chat(...)` telemetry emitted during skill execution (plus auto-extracted missing-item requirements via `summarize_chatlog` at `action.py:561-583`).
      3. `Critique:` generated by `CriticAgent` (`voyager/prompts/critic.txt`), which inspects post-action environment state and outputs JSON `{"reasoning": "...", "success": true/false, "critique": "..."}`. On failure, `critique` states *why* the goal was not met and *what concrete step* is needed next.
  - **Gemini 4 Argon**:
    - In `§2 Zero-shot control`, `/obs` returns a discrete `status` string (e.g., `if status == "grasp_failed", call robot.look_at(...) to re-observe and recover closed-loop`) alongside the updated `wrist_cam.png` with the cyan 3D pinch-center crosshair (`+`) and jaw brackets (`[ + ]`).
    - Contact primitives (`move_until_contact`, `place_until_contact`) terminate on physical motor lag (`max_lag=0.012`), turning contact into an execution-level event rather than an ungrounded open-loop coordinate guess.
  - **Anthropic**:
    - In `§03 Low-level manipulation`, para 4: `"After every movement, it receives images of the scene along with readings from the gripper’s force sensors, similar to what a VLA would receive."`
    - Adaptation (`§02 Simple settings`, para 9; `§05 Can they learn from experience?`, para 3 & 7) relies on seeing the immediate post-action sensory state (updated image + force sensor readings / reward or termination) over the last few steps.
- **Us (AionGenos)**:
  - **At `obs_rung="1"` and `"1b"` (`oracle_level == 1`)**: `format_round_feedback` (`aiongenos/orchestrator/push_feedback.py:47-56`) outputs **only** the open-loop command vs. proprioception readback:
    ```text
    DIAGNOSTIC REPORT FOR PREVIOUS ROUND:
      LEFT ARM:
        Target coordinate was predicted at: X=40 Y=20 Z=50
        Actual movement: from X=-40 Y=26 Z=53 to X=40 Y=20 Z=50
    ```
    Because the OSC servo tracks reachable workspace targets to median error `0.05 cm` (`wp3a_rung2p_diagnosis_2026-10-22.md` §1 table), `Actual movement` almost always matches `Target coordinate was predicted at` (`±1` grid unit) **whether or not the hand touched or moved the cube**. There is **no verdict line** (`push_feedback.py:15`: `"Without distances (rung < 2) there is no verdict"`) and no contact/force signal.
  - **At `obs_rung="2"` (`rung-2′` before `d2`, and after `d2`)**:
    - Before `d2` (`run 71134939`): `_p1_verdict` evaluated `cube_goal` distance on every round (`push_feedback.py:40, 55`). Before the hand contacts the cube, `cube_goal` never changes, so **547/547 rounds** printed: `"Result: No significant progress (still X.X cm from target). Try a different direction or larger step size."` (`wp3a_rung2p_diagnosis_2026-10-22.md` §2.1).
    - After `d2` (`--verdict_contact_switch`, `push_collect.py:273-280`): switches verdict from `tip_cube` (pre-contact) to `cube_goal` (after `first_cube_move`), **but only when `fb_scalars` is True (`obs_rung >= 2`)**. In `rung-1′` (`611a3e2a`, `663c049a`, `3786f4e5`), `d2` is a no-op because `obs_rung == "1"`.
- **Could the difference explain an observation of ours?**
  - **YES — explains three documented provenance phenomena**:
    1. **Active misdirection in `rung-2′` (`71134939`, `0/50`)**: Cited in `wp3a_rung2p_diagnosis_2026-10-22.md` §2.1 (lines 36–38) and `wp3a_push_provenance.md` (lines 2324–2327). Telling the model `"No significant progress ... Try a different direction"` on 547/547 rounds even when the fingertip moved closer to the cube caused the teacher to abandon approaching directions.
    2. **Rung-1 recap confabulation (44% at rung-1 `e4aebf36`, 42% at rung-1b `30f15f0c` vs. 0% at rung-2 `3e8c52d4`)**: Cited in `wp3a_push_provenance.md` § "2026-10-06 — pilot step (c), rung-1" (lines 1880–1885), § "2026-10-07 — rung-1b" (lines 1931–1933), and § "2026-10-08 — rung-2" (lines 2065–2068). At `obs_rung=1`, neither the per-round feedback nor the recap prompt (`build_push_recap_user_prompt`, `push_memory.py:383-387`) has any contact or cube-motion indicator — only `target → TCP reached` and `OUTCOME: failure`. Because TCP reached its target (`±1` unit), the recap VLM hallucinated that the cube moved (`"pushed away from the goal"`).
    3. **Premature `STOP: true` and blind-sweep continuation at `rung-1′` (`611a3e2a`: 9 premature STOPs, 30 plateaus; `wp3a_push_provenance.md` line 2379)**: `[speculative]` Unlike Anthropic (which feeds gripper force sensor readings in low-level manipulation, `§03 Low-level manipulation`, para 4) or Argon (which provides `/obs` `status` and `move_until_contact`), our `rung-1′` feedback gives only `TCP start → TCP end` and no contact/force signal, so the model must judge contact and cube motion purely from 256×256 oblique RGB frames (where vertical clearance of 4.3 cm is `< 2 px`, `wp3a_rung2p_diagnosis_2026-10-22.md` §2.3).

---

### 3.4 ALSO (1): Within-Episode History Handling & Image Retention

- **Them**:
  - **Anthropic**:
    - **Window**: Retains **first 10 turns + most recent $N$ turns** in truncation experiments (`§05 Can they learn from experience?`, para 6: `"In these truncation runs we always retain the first 10 turns plus the most recent N turns. Dropping the first turn caused models to forget basic conventions and loop, so we keep it in all conditions"`).
    - **Images**: Keeps **all prior frames** in the active window (`§07 Appendix -> Vision inputs -> Keeping prior frames`, para 1: `"All published vision cells kept prior frames in context"`).
    - **Effect**: Truncating old history did not hurt (and helped weaker models by avoiding `"context rot"`, `§05`, para 7), showing adaptation is short-range over the last few visual-action turns.
  - **Voyager**:
    - Keeps **zero multi-turn chat history** (`len(self.messages) == 2` asserted every step at `voyager/voyager.py:199, 267`). Every round builds a fresh `[system_message, human_message]` containing only the **last round's code**, **last round's execution error / chat log**, **current observation**, and **last round's critique**.
  - **Gemini 4 Argon**:
    - Multi-turn loop where the agent inspects the updated `wrist_cam.png` and `/obs` JSON each turn (`§2 Zero-shot control`, `Closed-Loop Turn Workflow`).
- **Us (AionGenos)**:
  - `EpisodeConversation` (`aiongenos/vlm/client.py:109-182`) keeps **Turn 0 (first user turn) + last 6 user/assistant pairs** (`DEFAULT_RECENT_WINDOW = 6`), **but strips `image_url` from all prior user turns on every new turn (`client.py:148-150`)**.
  - Consequently, on Round $r \ge 2$, the model sees:
    - **6 prior rounds of its own text `THOUGHT` + `LEFT_TARGET_POS` outputs and text `CRITIC FEEDBACK`**,
    - **0 prior scene images** (it cannot visually compare frame $r-1$ vs. frame $r$ to see whether the cube or arm moved in image space), and
    - **An orphaned `assistant` drop at Round 8+**: when `_prune_to_window()` runs (`client.py:116-130`), `self.messages[0]` (Turn 0 user) is followed directly by `tail[0]` (Round $r-6$ user), creating two consecutive `"role": "user"` messages in `self.messages`.
- **Could the difference explain an observation of ours?**
  - **YES — directly explains Observation §2.4 in `wp3a_rung2p_diagnosis_2026-10-22.md` ("History locks the height") and `wp3a_push_provenance.md` (lines 2315–2323)**:
    - In seed-paired comparison on seeds 5000–5049:
      - `rung-2` (**stateless**, `round_history=False, round_feedback=False`): **53% of rounds** targeted the contact band $Z \in [30, 40]$, and Round-2 emitted $Z=53$ in only **1/50 episodes**.
      - `rung-2′` (**history + feedback ON**, `round_history=True, round_feedback=True`): rounds in the contact band collapsed from **53% → 2%**, Round-2 $Z=53$ jumped from **1/50 → 45/50**, and **509/597 rounds (85%)** stayed locked at $Z=53$ (standby height $0.535\text{ m}$, $4.3\text{ cm}$ above the cube top).
    - **Why stripping prior images while keeping text history + feedback locks $Z=53$**: Because prior frames are stripped (`client.py:148-150`), the model cannot see a visual frame-to-frame diff between Round $r-1$ and Round $r$. Instead, it relies on the text history of its own previous `LEFT_TARGET_POS: X=... Y=... Z=53` and the text feedback `"No significant progress ... Try a different direction"`, which leads it to hold $Z=53$ constant as a "safe table plane" anchor and only perturb $X$ and $Y$.

---

### 3.5 ALSO (2): Output Format & Reasoning Budget

- **Them**:
  - **Gemini 4 Argon**:
    - `§2 Zero-shot control` → `## Execution Discipline` (verbatim):
      `"Simply output 1 sentence observation followed immediately by your curl command (with # Plan: on Turn 1 and # Thought: on every turn)."`
    - Keeps per-turn verbal output extremely compact (1 sentence observation + inline `# Thought:` comment) to focus tokens on the action call.
  - **Anthropic**:
    - `§05 What’s the bottleneck? -> Does reasoning help?`, para 1, 2, 5:
      `"Reasoning had little effect on most of our results... On the classic control tasks, newer models regressed when given a higher reasoning budget. This could be due to overengineering what are relatively simple experiments... On direct and high-level manipulation, reasoning made no major difference for any of the Claude-family models... Looking at the results across models, extra reasoning seems to hurt."`
  - **Voyager**:
    - Structured 3-part output (`voyager/prompts/action_response_format.txt`: `Explain: ... \n Plan: 1) ... \n Code: ```javascript ...````) at `temperature=0` (`voyager/voyager.py:32`).
- **Us (AionGenos)**:
  - `STAGE1_SYSTEM` (`prompts.py:47`): `"- Reason step-by-step about the physics before giving targets."`
  - `_S1_EEF_PUSH` (`prompts.py:168-171`):
    ```text
    THOUGHT: <one paragraph physics reasoning>
    LEFT_TARGET_POS: X=<int> Y=<int> Z=<int>        (required; ...)
    LEFT_TARGET_ORI: P=<int> Y=<int> R=<int>        (OPTIONAL; ...)
    STOP: <true|false>
    ```
  - Called at `temperature=0.7, max_tokens=2048` (`aiongenos/pipeline/stage1_reasoning.py:219, 265, 273`).
- **Could the difference explain an observation of ours?**
  - **Partially — explains free-form rationalizations overriding sensory evidence (`wp3a_rung2p_diagnosis_2026-10-22.md` §2.2, §2.3) and F30/F43 context bloat (`client.py:95-99`)**:
    - In `wp3a_rung2p_diagnosis_2026-10-22.md` §2.3 (line 46), in **83% of rounds** of `71134939` (`rung-2′`), the teacher's free-form `THOUGHT` paragraph rationalized the `~4.3 cm` vertical hover floor as a planar `XY` error and never questioned `Z=53` (real vertical reasoning occurred in only `25–46/597` rounds = `4–8%`, §1 line 21).
    - `[speculative]` Whereas Argon forces a 1-sentence visual observation first (`"Simply output 1 sentence observation..."`) before `# Thought:`, our `THOUGHT: <one paragraph physics reasoning>` does not require a structured check of `(a) where is the cube in (X,Y,Z)? (b) where is the green zone? (c) did my last move change Z to contact height?`. Over 6 retained turns, 6 verbose paragraphs of self-justifying prose accumulate in `EpisodeConversation`, reinforcing the initial `Z=53` assumption (echoing Anthropic's `"overengineering"` / `"context rot"` observation in `§05`).

---

### 3.6 ALSO (3): Exploration vs. Exploitation (Avoiding Copying the Last Success)

- **Them**:
  - **Voyager**: Uses four explicit mechanisms to prevent copying a previous action blindly:
    1. **Code parameterization (`action_template.txt` rule 3)**: `"Your function will be reused for building more complex functions. Therefore, you should make it generic and reusable. You should not make strong assumption about the inventory..."`
    2. **Anti-copying rule for failed/previous round (`action_template.txt` rule 4)**: `"Functions in the 'Code from the last round' section will not be saved or executed. Do not reuse functions listed there."`
    3. **Explicit random exploration rule (`action_template.txt` rule 7)**: `"Use exploreUntil(bot, direction, maxDistance, callback) when you cannot find something... You should select a direction at random every time instead of constantly using (1, 0, 1)."`
    4. **Curriculum anti-repetition (`curriculum.txt` rule 5)**: `"The next task should be novel and interesting... I should not be doing the same thing over and over again."`
  - **Anthropic**:
    - Identifies sequence memorization as a fundamental failure mode of raw in-context trajectory examples (`§05 Can they learn from experience?`, para 12, on `oneshot_course`): `"On harder, longer courses, practice does not help. On those trials, neither Mythos Preview nor Opus 4.7 completes a single trial even with twenty practice runs. The models are learning a specific sequence and are not yet general planners."`
  - **Gemini 4 Argon**:
    - Avoids single-trajectory copying by prompting the model to write a **closed-loop policy / trajectory generator** tested across `±10 cm pose randomization` (`§ Unlocking research and self-improvement -> 1. Action improvement via simulation`, Prompt item 3) or by requiring visual verification of the reticle on `wrist_cam.png` before acting (`§2 Zero-shot control`).
- **Us (AionGenos)**:
  - **Buffer retrieval (`aiongenos/memory/recap_buffer.py:242-277`)**: `success_floor_frac = 2/3` forces the first 1–2 successes in the buffer into **every** subsequent episode's top-3 preamble.
  - **Preamble instruction (`aiongenos/orchestrator/push_memory.py:571-579, 635-636`)**: `"Use these to choose a better target for the current scene"` / `"Use the past lessons above to choose your target for this current scene."` There is **no warning** that the cube and green goal zone are randomized to different positions in every episode (`Pin-4c ±75°`) and that past coordinates/directions must **not** be copied unless the current image matches.
  - **Recap generation prompt (`build_push_recap_system_prompt`, `push_memory.py:339`)**: Explicitly tells the recap writer `"You MAY cite the numbers given below; they are physical facts"`, which encourages recaps to bake episode-specific numbers into `LESSON: ...` (requiring `COORD_PATTERN` regex redaction when `preamble_coords="off"`).
- **Could the difference explain an observation of ours?**
  - **YES — directly explains the "memorized blind sweep" in `611a3e2a` and `663c049a` (`wp3a_push_provenance.md` §2026-10-22 lines 2382–2388; §2026-10-27 lines 2466–2476)**:
    - Exactly as Anthropic observed on `oneshot_course` (`"The models are learning a specific sequence and are not yet general planners"`), when our preamble exposed the raw target coordinates of a prior success (`preamble_coords="on"`) with `similarity=0.98+` and a `2/3` success floor, Gemma-4-31B treated the retrieved episode as a sequence to replay (`35/40` copies in `611a3e2a`, `37/49` copies in `663c049a`).
    - Even with `preamble_coords="off"` (`3786f4e5`), while coordinate redaction prevented verbatim tuple copying (raising unique R1 targets to `42/50` and SR to `13/50`), `build_push_recap_system_prompt` (`push_memory.py:335-340`) still asks for `"ONE concrete adjustment"` without requiring the lesson to state **conditional** visual logic (e.g., *"If the green zone is to the left (+Y) of the yellow cube, aim to the right (-Y) of the cube"*). `[speculative]` If a success recap says *"LESSON: Aim slightly to the left of the cube and push forward"*, retrieving it under the `2/3` success floor on an episode where the goal is at `-75°` (to the right) can still bias direction consistency unless the lesson is explicitly conditional on visual layout.

---

### 3.7 ALSO (4): Spatial/Visual Grounding Aids, Action Primitives & Simulator Pausing

- **Them**:
  - **Gemini 4 Argon (`§2 Zero-shot control`)**:
    1. **Explicit axis convention in prompt**: `+X (UP in image): Away from robot base | -X (DOWN): Towards robot base; +Y (LEFT in image): World left | -Y (RIGHT): World right; +Z: Height above table`.
    2. **Visual coordinate harness on image**: 2 cm world `(X, Y)` grid drawn in yellow numbers at `grid_z` on `wrist_cam.png`, plus cyan 3D pinch-center crosshair (`+`) and jaw brackets (`[ + ]`), plus `robot.deproject(u, v, z_plane)`.
    3. **Contact-terminated primitives**: `move_until_contact(dz=-0.06, ...)`, `place_until_contact(...)`.
  - **Anthropic (`§02`, `§03`, `§04`, `§05`, `§07`, `§08`)**:
    1. **Gripper-cam interactive cursor (`--crosshair --gripper-cam`)**: Model moves a red `X` on the gripper cam and queries object identity + distance at that point → lifts Mythos Preview manipulation SR on 10-task LIBERO subset from **6% → 32%** (`§05 Is visual perception the bottleneck?`, para 5).
    2. **Compass (`compass`)**: Text world-frame heading in degrees appended each frame → lifts all locomotion configs (`§05`, para 5; `§07 Vision tools`, para 2).
    3. **`ask_vlm` (`--vision-mode ask_vlm`)**: Replaces raw images with text scene descriptions from Gemini 3.1 Pro Preview → helps older Claude models (`Opus 4 / 4.1`) that struggle with pixel-level spatial extraction, but hurts stronger vision models (`Opus 4.6 / 4.7`, `Gemini 3.1`) (`§05`, para 6–8; `§07`, para 3).
    4. **Simulator pausing**: Pauses MuJoCo between LLM calls in direct/code control (`§02`, para 4; `§08`, para 5) so 5–60 s API latency does not cause trivial control failure, while noting that the fixed-base Panda arm in manipulation did not require pausing between calls (`§03 Low-level manipulation`, para 5; `§08 Latency`, para 6).
- **Us (AionGenos)**:
  - **Axis convention (`d1`, `format_frame_convention_line` at `aiongenos/vlm/prompts.py:394-411`)**: Added on 2026-10-22 (`wp3a_push_provenance.md` line 2343) after the Argon review in `wp3a_rung2p_diagnosis_2026-10-22.md` §4:
    `FRAME (base frame, same grid as the numbers above): +X = forward, away from the robot base; +Y = the robot's left; +Z = up. One grid unit = 0.45 cm in X, 0.40 cm in Y, 0.35 cm in Z.`
    **Difference vs. Argon**: Argon's axis convention maps world axes **to image directions** (`"+X (UP in image): Away from robot base"`, `"+Y (LEFT in image): World left"`). Our `d1` line defines `+X`, `+Y`, `+Z` relative to the **robot base** (`"forward, away from the robot base; +Y = the robot's left"`), without stating which way `+X` and `+Y` point in the **front camera image** (where the camera looks from the front/side at an oblique angle) or in the **top-down camera image** (`image top = robot +x`, `wp3a_push_provenance.md` line 1907).
  - **Primitives**: Direct 3D TCP waypoint + 3D orientation offset (`LEFT_TARGET_POS`, `LEFT_TARGET_ORI`), executed for `steps_per_segment = 90` steps (`1.5 s` at 60 Hz) via OSC impedance control; simulator is naturally paused between 90-step segments while `run_stage1_eef` awaits the synchronous HTTP response (`push_collect.py:310-340`). Contact-terminated descent (`d3-i`) was explicitly rejected by the PI on 2026-10-22 (`wp3a_push_provenance.md` lines 2361–2364) because it confiscates the $Z$ degree of freedom and would rely on GT distance in simulation.
- **Could the difference explain an observation of ours?**
  - **YES — directly explains two major provenance transitions and one remaining gap**:
    1. **Pre-`d1` axis inversion (`71134939` rung-2′: 536/597 moves Y-dominant, 62–64% of thoughts calling Y the forward/push axis) vs. Post-`d1` fix (`611a3e2a` rung-1′: 74/155 thoughts cite `+X` forward, 11/50 successes)**: Documented in `wp3a_rung2p_diagnosis_2026-10-22.md` §2.2 (lines 39–42) and `wp3a_push_provenance.md` (line 2389). Giving `d1` completely eliminated the Y-forward axis inversion.
    2. **Why `rung-1b` (top-down camera without `d1` or image-axis mapping, `run 30f15f0c`) got 0/50 and clustered at grid zero (`68%` X=0)**: Documented in `wp3a_push_provenance.md` § "2026-10-07 — pilot step (c), rung-1b" (lines 1928–1930). Anthropic found that adding a new camera view (`third_person`) or raw `depth` overlay is neutral or hurts unless paired with orientation grounding (`compass` / `cursor`, `§05 Is visual perception the bottleneck?`, para 3–5). In our `rung-1b`, `TOP_VIEW_SENTENCE` (`push_memory.py:61`) says only `"The last image is a top-down view of the current scene."` without telling the VLM how the image axes align with base-frame `(X, Y)` (`image top = +X, image left = +Y`).
    3. **Remaining low stimulus tracking in `Pin-4c` (`3786f4e5`: $\rho_X = -0.098$, $\rho_Y = +0.278$, `Z=53` in `37/150` rounds; `wp3a_push_provenance.md` line 2469)**: `[speculative]` In the front camera image (`124°` FOV at `256×256`, `wp3a_rung2p_diagnosis_2026-10-22.md` §2.3), `d1` tells the model `+X = forward, +Y = robot's left, +Z = up`, but does not tell the model where the camera is mounted relative to the robot base (i.e., whether "robot's left `+Y`" is left or right in the front RGB image) or what table surface height `Z` corresponds to in grid units (while standby `LEFT_EE_POS` starts at `Z=53`).

---

### 3.8 Summary Comparison Matrix

| Dimension | Voyager (`MineDojo/Voyager`) | Gemini 4 Argon (`googleblog`) | Anthropic (`Claude plays robotics`) | AionGenos (`WP1-③a` Push) | Provenance Observation Explained |
|---|---|---|---|---|---|
| **(1) Identity & Embodiment** | Single-bot JS coder (`action_template.txt`); unused state masked in warmup (`curriculum.py:821`). | Exact active limb per task; explicitly retracts inactive hands (`§3 Omni control`). | Fixed template filled with active embodiment's exact joints/sensors (`§07 Prompts`). | `STAGE1_SYSTEM`: `"bimanual … both arms"` + `RIGHT_EE_POS` shown while right arm is frozen (`prompts.py:42, 151`). | Flagged in `wp3a_rung2p_diagnosis_2026-10-22.md` §1a; distractor 3D state tokens `[speculative]`. |
| **(2) Memory Preamble** | Top-5 executable JS skill functions in `SystemMessage` every round; **similarity scores discarded** (`skill.py:126`). | No retrieval preamble; consolidates 4,500+ sim episodes into VLA weights (`§4.1`). | No cross-episode retrieval; keeps all prior frames in-context (`§07 Keeping prior frames`). | Top-3 recaps on Round 1 only; shows `(similarity=0.9xx)` (`state_sim≈1`); **strips past images on Round 2+** (`client.py:148`). | Directly explains `(e)` path copying (`611a3e2a` 35/40; `663c049a` 37/49 vs `3786f4e5` 13/50, `wp3a_push_provenance.md` §2026-10-27). |
| **(3) Feedback Form** | JS error + chat log + JSON Critic (`reasoning`, `success`, `critique` with concrete fix, `critic.txt`). | `/obs` `status` (`grasp_failed` recovery) + wrist reticle + `move_until_contact` (`§2.2`). | Post-move RGB + gripper force sensors (`§03 Low-level manipulation`, para 4). | Rung-1: TCP predicted vs. actual only, **no verdict / no contact signal**; Rung-2′ pre-`d2`: flat `cube_goal` verdict. | Explains `rung-2′` 547/547 misleading verdicts (`diagnosis` §2.1) & `rung-1/1b` 42–44% recap confabulation (`provenance` §2026-10-06/08). |
| **(4) History Handling** | Stateless 2-message rewrite (`[System, Human]`) every step (`voyager.py:262`). | Multi-turn closed-loop inspecting updated `wrist_cam.png` + `/obs` (`§2.2`). | Retains **first 10 + recent $N$ turns**; **keeps all prior frames** (`§05` para 6; `§07`). | Keeps **Turn 0 + last 6 pairs**, **strips all prior images** (`client.py:148`), leaving text-only history + consecutive user turns at R8+. | Directly explains `rung-2` (stateless, 53% contact Z) vs `rung-2′` (history ON, 2% contact Z, 45/50 R2 `Z=53`) height-locking (`diagnosis` §2.4). |
| **(5) Output Format & Reasoning** | `Explain` + `Plan` + `Code` at `T=0` (`action_response_format.txt`). | `1 sentence observation` + `# Plan:` (T1) / `# Thought:` + `curl` (`§2.2`). | Extra reasoning budget **neutral or hurts** control/manipulation due to overengineering (`§05 Does reasoning help?`). | Free-form paragraph `THOUGHT` + `LEFT_TARGET_POS` / `ORI` / `STOP` at `T=0.7, max_tokens=2048` (`prompts.py:168`). | Explains 83% XY rationalization of vertical hover error (`diagnosis` §2.3) & F30/F43 CoT drift (`client.py:95`). |
| **(6) Exploration vs. Exploitation** | Parameterized functions (`rule 3`), no last-round reuse (`rule 4`), random explore dir (`rule 7`), write-on-success only. | Closed-loop generator over `±10 cm` pose randomization (`§4.1`). | Practice runs on `oneshot_course` memorize a sequence and fail on hard courses (`§05` para 12). | `2/3` success floor + `state_sim≈1` + `"Use these to choose a better target"`; recaps invited to cite raw numbers (`push_memory.py:339`). | Explains why a single lucky success hijacks all later episodes under `coords="on"` (`611a3e2a`, `663c049a`). |
| **(7) Grounding Aids & Pausing** | Text/voxel coordinates (`Position: x=..., y=..., z=...`). | Axis-to-image mapping (`+X UP in image`), 2 cm image grid, `move_until_contact` (`§2.2`). | Gripper-cam `cursor` (`6%→32%`), `compass`, `ask_vlm`, sim paused between calls (`§02`, `§05`, `§08`). | `d1` base-frame axis/unit line (`prompts.py:408`); no camera-to-axis mapping; sim paused between 90-step segments. | `d1` fixed the 62–64% Y-axis inversion (`611a3e2a`), while missing image-axis mapping explains `rung-1b` 68% X=0 clustering (`provenance` §2026-10-07). |

---

## 4. Conclusion: Candidate Prompt Changes for the PI (No Code Changes)

Below are **7 concrete candidate prompt changes** distilled from the external review and our provenance diagnostics, ordered by expected leverage and zero-oracle compliance (all preserve the PI's `IMAGE + PROPRIOCEPTION ONLY` rule at `obs_rung=1`).

| # | Target Location | Candidate Prompt Change | External Source Anchor | Provenance Motivation & Expected Effect |
|---|---|---|---|---|
| **C1** | `aiongenos/vlm/prompts.py` (`STAGE1_SYSTEM`, `_S1_EEF_PUSH`) & `scripts/run_push_collect.py` (`instruction`) | **Align identity framing to single-arm push**: Remove `RIGHT_EE_POS` from `_S1_EEF_PUSH` (or explicitly state in `instruction` / `_S1_EEF_PUSH`, matching `L0A_SINGLE_REACH_LEFT` in `task_instructions.py:18-20`, that *"Your right arm is parked and held still — you only control the left arm"*), and scope `STAGE1_SYSTEM` for single-arm tasks so it does not instruct `"plan the next sub-goal for both arms"`. | **Argon** (`§2 Zero-shot control`, `§3 Omni control` bullet 2); **Anthropic** (`§07 Appendix -> Prompts`, para 1); **Voyager** (`curriculum.py:821` warmup masking). | Resolves the P1 vs. push discrepancy flagged in `wp3a_rung2p_diagnosis_2026-10-22.md` §1a. Eliminates contradictory bimanual instructions and distractor `RIGHT_EE_POS` coordinates `[speculative: cleaner attention on `LEFT_EE_POS`]`. |
| **C2** | `aiongenos/orchestrator/push_memory.py` (`format_push_preamble_text`, `build_push_recap_system_prompt`) | **Lock `preamble_coords="off"`, drop `(similarity=0.9xx)` badge, and require conditional visual rules in recaps**: (a) Keep `preamble_coords="off"` as default and instruct `build_push_recap_system_prompt` (`push_memory.py:335-340`) **not** to cite raw grid coordinates (`X=..., Y=..., Z=...`), but instead to write a **conditional visual rule** (how to adjust relative to where the yellow cube and green zone appear in the image); (b) remove `(similarity={s:.3f})` from `[PAST EPISODE i]` (since `0.6 * state_sim = 0.600` is constant across all episodes) and add an explicit anti-copying caveat: *"The cube and green zone are in DIFFERENT positions in every episode; do NOT copy a past direction blindly — apply the lesson to the CURRENT scene's visual layout."* | **Voyager** (`skill.py:126` discards similarity scores; `action_template.txt` rules 3, 4, 7 anti-copying & parameterization); **Anthropic** (`§05` para 12 `oneshot_course` sequence-memorization warning). | Grounded in `(e)` (`wp3a_push_provenance.md` §2026-10-27: `coords="off"` raised SR `3/50 → 13/50`, unique R1 targets `10 → 42`). Dropping the inflated `0.98x` badge and enforcing conditional lessons directly targets the remaining $\rho_X = -0.098$ gap and prevents single-direction bias across the 300-episode life run. |
| **C3** | `aiongenos/orchestrator/push_memory.py` (`_PUSH_PREAMBLE_HEADER*`) & `aiongenos/vlm/client.py` (`EpisodeConversation`) | **Fix Round 2+ stripped-image preamble mismatch**: Since `client.py:148-150` strips `preamble_image_base64_list` from Turn 0 on Round 2+, either (a) replace the Turn-0 preamble header on Round 2+ with text-only wording (*"PAST EPISODE LESSONS (images shown on Round 1 only)"* and drop `"Image i: the scene at the start of that episode"`), or (b) keep the previous round's scene image ($r-1$) in `EpisodeConversation` so Round $r$ can visually diff Round $r-1$ vs. Round $r$. | **Anthropic** (`§07 Appendix -> Vision inputs -> Keeping prior frames`, para 1: keeps prior frames in context; `§05` para 5–7: adaptation is short-range over recent visual turns). | Addresses `wp3a_rung2p_diagnosis_2026-10-22.md` §1a & §2.4. Eliminates dangling `"Image 1/2/3"` references on Rounds 2–12, and (if $r-1$ image is kept) lets the teacher visually see whether the arm descended or the cube moved between consecutive rounds `[speculative]`. |
| **C4** | `aiongenos/vlm/prompts.py` (`format_frame_convention_line`, `TOP_VIEW_SENTENCE`) | **Extend `d1` frame line to map base axes to camera image directions**: Append camera-to-base orientation to `format_frame_convention_line` (e.g., stating how `+X` forward, `+Y` robot-left, and `+Z` up project into the front camera view, and at `rung-1b+` stating in `TOP_VIEW_SENTENCE` that in the top-down view `UP in image = +X (forward), LEFT in image = +Y (robot's left)`). | **Gemini 4 Argon** (`§2 Zero-shot control -> Visual Coordinate Reference`: `"+X (UP in image): Away from robot base ... +Y (LEFT in image): World left"`); **Anthropic** (`§05` para 5: `compass` / orientation grounding beats raw extra views). | Grounded in `wp3a_rung2p_diagnosis_2026-10-22.md` §2.2 & `wp3a_push_provenance.md` §2026-10-07 (`rung-1b` `30f15f0c` had `68%` X=0 clustering because the top view had no image→grid axis mapping). Expected to improve round-1 directional alignment ($\theta$ consistency and $\rho_X / \rho_Y$) without revealing object coordinates. |
| **C5** | `aiongenos/orchestrator/push_feedback.py` (`format_round_feedback`) & `aiongenos/vlm/prompts.py` (`_S1_EEF_PUSH`) | **Anti-anchoring feedback note at `obs_rung=1`**: Clarify in `format_round_feedback` at `obs_rung < 2` that `Actual movement: from ... to ...` measures **only** the fingertip (TCP) in free space and **does not confirm cube contact** — the model must check the updated image to verify whether the yellow cube actually moved, and if the cube did not move, it must adjust **height (`Z`, lowering below the `Z=53` standby hover)** or **`(X, Y)` alignment** rather than repeating the same `Z`. | **Voyager** (`critic.txt` separates action execution from task-completion verification); **Argon** (`§2.2` `Closed-Loop Turn Workflow` step 3: verify visually after every turn in updated camera view); **Anthropic** (`§05` para 3: revise strategy after failed attempts). | Directly targets the `Z=53` standby height-locking mechanism (`wp3a_rung2p_diagnosis_2026-10-22.md` §2.4: `rung-2` stateless had `53%` rounds in contact band $Z \in [30,40]$, whereas `rung-2′` with history+feedback dropped to `2%` and locked `Z=53` in `45/50` Round-2 turns). |
| **C6** | `aiongenos/vlm/prompts.py` (`_S1_EEF_PUSH`) | **Structured 2-sentence `THOUGHT` slot (Observation → 3D Adjustment)**: Replace generic `THOUGHT: <one paragraph physics reasoning>` with a structured prompt instruction: `THOUGHT: <1 sentence stating where the yellow cube and green zone are relative to the fingertip in the image, then 1 sentence choosing (X, Y) behind the cube and a contact height Z below the standby hover>`. | **Gemini 4 Argon** (`§2 Zero-shot control -> Execution Discipline`: `"Simply output 1 sentence observation followed immediately by your curl command (with # Plan: on Turn 1 and # Thought: on every turn)"`); **Anthropic** (`§05 Does reasoning help?`, para 2 & 5: unstructured extra reasoning regresses/hurts via overengineering). | Addresses `wp3a_rung2p_diagnosis_2026-10-22.md` §1 & §2.3 (where real vertical reasoning occurred in only `4–8%` of rounds and `83%` of rounds misread the `4.3 cm` vertical floor as an `XY` error). Forces explicit `(X, Y, Z)` visual grounding in every turn while shrinking multi-turn context bloat `[speculative]`. |
| **C7** | `aiongenos/vlm/client.py` (`EpisodeConversation._prune_to_window`) | **Preserve Turn-0 assistant response or separator when pruning history window**: When `len(self.messages) > 2 * recent_window + 1`, either retain `self.messages[:2]` (Turn-0 user + Turn-0 assistant) before `tail`, or re-inject only the system/preamble header into the first retained user turn so pruning at Round 8+ does not concatenate two consecutive `"role": "user"` messages (`self.messages[0]` followed by `tail[0]`). | **Anthropic** (`§05 Can they learn from experience?`, para 6: `"retain the first 10 turns plus the most recent N turns"` as complete turns); **Voyager** (`voyager.py:195` clean `[SystemMessage, HumanMessage]` structure). | Prevents malformed `[user, user, assistant, ...]` chat alternation in episodes reaching Rounds 8–12 (`client.py:125-129`) `[speculative: affects long episodes > 7 rounds]`. |

---
**Lead acceptance note (isaac, 2026-10-28):**
- **Verified by qa1** (`evidence/2026-10-28_p2mem/verify_prompt_qa1.md`): the §2 reconstruction matches the code, rendered on CPU; the external quotes were spot-checked verbatim.
- **Founding-intent classification of C1–C7 by mem1** (`evidence/2026-10-28_p2mem/intent_review_mem1.md`):

  | Change | Classification |
  |---|---|
  | C1 | IN, conditional (touching `STAGE1_SYSTEM` breaks Rule 10 byte-identity) |
  | C2 | coords/badge part: IN; recap-rule part: strategy injection (OUT) |
  | C3 | option (a) IN; option (b) invalidates Rule 10 |
  | C4 | IN; a frame-plumbing extension, ledger entry e |
  | C5 | OUT (strategy/conditional) |
  | C6 | OUT (strategy/conditional) |
  | C7 | IN (pure engineering) |

- **No prompt change has been made.** Every change waits for a PI ruling, then a Rule 10 amendment, then a ladder re-run from rung-1′.
