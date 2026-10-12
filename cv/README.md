# leafy-cv

Computer vision worker for Leafy AI. It is a separate uv project (Python 3.12) so PyTorch and
OpenCV never become dependencies of the API server. The backend only reads the results from Supabase.

## Setup

```powershell
cd cv
uv sync
uv run pytest
```

## Step 1: index the archived frames

Frames are expected as `<frames-root>\<camera_id>\<camera_id>_YYYYMMDD_HHMMSS.jpg`.

```powershell
uv run python tools/build_frame_index.py --frames-root E:\Claude
```

It takes about 1 s per frame and needs `trained/plant_filter.json` (step 3). Run it over **all** frames since
the first one (periods are numbered from the first frame), and back up `data/periods.csv` first: the rebuild
writes it again with empty notes, so copy the notes back. Each frame is checked two
ways against the last trusted frame:

- **Has the camera moved?** Corners are matched only on each camera's fixed parts (frame rails, walls,
  light bar), listed in `config/fixed_parts.json`, so growing leaves can't fake a move. If a camera is
  turned and its fixed parts change, redraw its rectangles there.
- **Have the plants changed?** The plant filter scores 16 px tiles; `plant_change` is the share of tiles
  that switched between plant and not plant with no plant within one tile (so swaying and growing leaves
  don't count). Above 0.045 means plants were moved, removed or arrived.

The first frame of each day can be OK but never becomes the reference: camera 1 is often shifted
5-8 px then, and the morning light differs.

This writes (all under `cv/data/`; git ignores `data/` except `frame_index.csv` and `periods.csv`, which are tracked because they were corrected by hand on 11 Oct and must not be rebuilt):

| File | What it is |
| --- | --- |
| `frame_index.csv` | One row per frame: period, status, whether it's usable, and the measured shift |
| `periods.csv` | One row per camera period. Each period needs its own hole map. Fill in `note`. |
| `checks/events/*.jpg` | A before/after image for every frame whose status isn't `ok` |

Frame statuses:

| Status | Meaning | Usable? |
| --- | --- | --- |
| `ok` | Same camera position as the last trusted frame | yes |
| `transient_shift` | A one-off: different from the frames before and after (camera 1's morning shift, morning light) | no |
| `camera_moved` | First frame of a lasting new camera position (50+ fixed-part corners agree on a shift over 5 px) | yes, with the new period's hole map |
| `scene_changed` | First frame of a lasting change in where the plants are (moved, removed or arrived), or the camera was turned so far its fixed parts are out of view. Open its event image and write which in `periods.csv` | yes, with the right hole map |
| `unstable` | Different from both the frame before and the frame after | no |
| `unconfirmed` | Different from before, and there is no later frame yet to decide | no, wait for the next frame |

`first_of_day` marks each day's first frame; `plant_cover` is the share of the frame that looks like plant.

## Step 2: hole maps (one per camera period)

A hole map is `hole_maps/<camera_id>_<period>.json`: the centre of every planting hole in that
camera's view, clicked on one reference frame. Hole maps are tracked by git (unlike most of `data/`).

Make or correct one (opens the existing file if there is one):

```powershell
uv run python tools/click_holes.py --period P2 --frame E:\Claude\level1_camera2\level1_camera2_20260922_130030.jpg
```

Rows are numbered by distance from the camera: click the row farthest from the camera first (row 1)
and the nearest row last. The tool opens on row 1. Left click adds a hole, right click deletes the
nearest one, `n`/`p` move to the next/previous row, `e` marks new clicks as estimated (a hole hidden
under leaves, drawn orange), `u` undoes, `s` saves, `q` saves and quits, `x` quits without saving.

Where the canopy is so dense that plant bases can't be seen (the rows beyond row 1), outline it as a
zone instead of guessing holes: press `z`, click its corners, press `z` again (3+ corners; right click
removes the last corner). `d` deletes the last zone. A zone is measured as a whole, as closure (the
share covered by leaves), and may overlap row-1 cells. Saving keeps the map's existing zones and notes.

Check it:

```powershell
uv run python tools/check_hole_map.py --hole-map hole_maps/level1_camera2_P2.json --frames-root E:\Claude
```

This prints six PASS/FAIL checks and writes `data/checks/hole_maps/<camera>_<period>.jpg`: the cells
and zones drawn on the first, middle and last usable frames of the period. Pass when every dot sits on
its hole (or stem base) in all three frames, zones cover only the closed canopy, and no check says FAIL.

Holes whose cell is less than 85% inside the frame (`MIN_IN_FRAME`) are still measured but left out of
readiness decisions and evaluation, because we can't see the whole plant. The check tool lists them and
the overlay marks them with a red ring and "x". Nothing needs to be set by hand.

Hole IDs are `L{level}-C{camera}-R{row}-H{position}`, rows numbered by distance from the camera (row 1 = farthest),
positions from the left.

**Channels.** Crowding is measured in both directions (corrected 12 Oct; the 7 Oct version measured only across
channels, from a misunderstanding): channel expansion separates the plants *in the same channel*, and plants
touching the next channel also need space before they go to Level 2. A map's `channel_axis` says which holes share
a channel: `"row"` (the default; cameras 1 and 2 see the channels run left-right) or `"col"` (camera 3 looks
along them). New maps: `click_holes.py --channel-axis col`; existing maps keep theirs. Each hole is paired with
the next hole along its channel ("along"; a gap far longer than the gaps next to it, i.e. a missing hole, is
skipped) and with the facing hole(s) in the adjacent channel(s) ("across"); the check tool counts both and lists
any hole without a partner.

**Dates.** A map covers `valid_from` to `valid_to`. For the camera's latest period `valid_to` is empty, so the
map keeps covering new frames until the layout changes again (then rebuild the frame index and close it).

## Step 3: segmentation and the plant filter

MobileSAM outlines the object at each hole centre; a small trained filter then decides whether each
outline is plant (leaf or stem) or not (board, hole, pot, wall, glare). Setup, once:

```powershell
uv sync
uv run python tools/download_weights.py
```

Then:

1. `uv run python tools/make_mask_candidates.py --frames-root E:\Claude` makes outlines to label from a
   spread of frames (already done: `labels/plant_masks/` has 644). Don't rerun it once labelling has
   started: new outlines wouldn't match the answers.
2. `uv run python tools/label_masks.py --frames-root E:\Claude` shows each outline; press `y` plant,
   `n` not plant, `m` mixed, `s` skip, `b` back, `q` quit. Answers save after every key. Aim for 400.
3. `uv run python tools/train_plant_filter.py --frames-root E:\Claude` trains it, prints its accuracy
   on frames it never saw, and writes `trained/plant_filter.json` and
   `data/checks/plant_filter_errors.jpg` (its worst mistakes, to look at).

The filter judges colour and texture only, never size: a closed canopy is one huge outline and is
still plant.

## Step 4: run the pipeline (numbers, statuses, overlays)

```powershell
uv run python tools/run.py --hole-map hole_maps/level1_camera2_P2.json --frames-root E:\Claude
uv run python tools/run.py --hole-map hole_maps/level1_camera1_P3.json hole_maps/level1_camera2_P3.json hole_maps/level1_camera3_P4.json --frames-root E:\Claude
```

New frames: rebuild the frame index (step 1) first. `run.py` refuses a map that is still open when frames on
disk are newer than the index, and reports a layout change that has no hole map yet; either ends the run with a
PROBLEMS list and exit code 1, so out-of-date statuses can't pass silently.

For every usable frame of the map's period (from `data/frame_index.csv`), MobileSAM outlines the plant at each
hole; the plant filter keeps, per hole, the largest outline that is plant and not far bigger than the cell.
Per hole:

- `coverage`: share of its cell covered by plant.
- `boundary_contact`: do its leaves meet the leaves of a neighbouring plant, in the same channel or the next
  channel? Nine parallel lines run from the plant's centre to each partner's; a line is closed when leaves run
  continuously along it, with no visible board between the two plants. Contact = closed lines / 9 for the
  partner it touches most, in either direction (0 = board visible everywhere between them, 1 = leaves meet
  across the whole width). `contact_along` / `contact_across` give the same per direction.
- `plant_area_px`: size of its own outline.

Per zone: `closure` (MobileSAM prompted on a grid inside the zone, at most 150 points). Then the readiness rule
(`leafy_cv/readiness.py`) gives each hole a status per frame: `empty`, `growing`, `candidate` (crowded: contact,
as a median of the last 3 frames, at least 0.5), `ready` (crowded 3 usable frames in a row: expand),
`uncertain` (mostly outside the frame). Only `ready` is an alert for the grower ("check today"); `candidate`
becomes `ready` or drops back within 2 frames, so it is not shown. Output in `data/runs/<camera>_<period>/`: `observations.csv` (one row per
frame x hole/zone), `gaps.csv` (one row per frame x pair of plants; `direction` along = same channel, across = next channel), `overlays/` (red line
between two plants = their leaves meet), `timeline.png` (status of every hole in every frame). About 10-30 s per
frame on a laptop CPU. Rerunning only measures new frames (the plant pixels are kept in `masks/`) and never adds
duplicate rows; changing the readiness rule needs no MobileSAM rerun.

## Step 5: check the readiness rule with our own labels

There is no grower round, so we label against the written rule: "do this plant's leaves touch the leaves of any
neighbouring plant, in the same channel or the next channel?"

1. `uv run python tools/make_hole_items.py` picks ~240 hole crops stratified by camera and CV status (ready, growing,
   candidate, empty), at most one per hole per day, never from the plant-filter training frames.
   Writes `labels/readiness/items.csv` and `strata.csv`.
2. `uv run python tools/label_holes.py --frames-root E:\Claude`: `y` crowded, `n` not yet, `e` empty, `u` unsure.
   No numbers are shown. About 20 minutes per 100.
3. `uv run python tools/evaluate_readiness.py`: the frozen rule against the labels, per camera and per CV status,
   crowded plants caught vs missed, with 95% intervals. Rules are not changed after seeing these numbers.

## Licences

This project must stay closed-source-compatible (possible commercialisation). Use only permissively
licensed dependencies (MIT, BSD, Apache-2.0). **No Ultralytics packages** (YOLO, FastSAM): they are
AGPL-3.0. Segmentation uses MobileSAM (Apache-2.0). Licence check of every installed package (4 Oct 2026): all direct
dependencies are BSD or Apache-2.0 (torch, torchvision, timm, MobileSAM, scikit-learn, OpenCV, numpy); three they pull
in use other permissive licences (tqdm MPL-2.0/MIT, typing_extensions PSF-2.0, pillow MIT-CMU). All allow closed-source
commercial use. On Linux, PyPI's torch also installs NVIDIA CUDA libraries (proprietary, freely redistributable); a
server should install the CPU build of torch.

## Modules

- `leafy_cv/frames.py`: finds frames on disk and reads camera + time from the file name.
- `leafy_cv/drift.py`: measures how far the camera moved between two frames (ORB keypoints on fixed parts + RANSAC).
- `leafy_cv/scene.py`: where the plants are, in 16 px tiles, and how much that changed between two frames.
- `leafy_cv/frame_index.py`: turns those measurements into frame statuses and periods.
- `leafy_cv/hole_map.py`: loads/saves hole maps and builds each hole's cell, neighbours, partners in both directions and gap corridors.
- `leafy_cv/segment.py`: MobileSAM prompted at points, with neighbours as "not this" points.
- `leafy_cv/plant_filter.py`: colour and texture features of an outline, and the trained plant filter.
- `leafy_cv/metrics.py`: per-frame numbers: outline choice, coverage, boundary contact, zone closure.
- `leafy_cv/readiness.py`: the readiness rule (statuses from the numbers, 3-frame streak, hysteresis).
