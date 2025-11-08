# Scene-Level Video Generation - Visual Flow

## Problem: Before Fix ❌

```
User clicks "Tạo Video" on Scene 2
       ↓
Signal emitted: generate_video_requested(scene_idx=2)
       ↓
    ❌ NO HANDLER CONNECTED
       ↓
    Nothing happens
```

```
Retry scenario (if it worked):
       ↓
Scene index not tracked properly
       ↓
Video generated with wrong index
       ↓
❌ Video saved as scene_1.mp4 instead of scene_2.mp4
       ↓
❌ Scene 1's video overwritten
```

## Solution: After Fix ✅

### Image Regeneration Flow

```
User clicks "🔄 Tạo lại" on Scene 2
       ↓
Signal: recreate_requested(scene_idx=2)
       ↓
✅ _on_scene_recreate_image(scene_idx=2)
       ↓
Find scene where scene.index == 2
       ↓
Create temp_outline = {"scenes": [scene_2_data]}
       ↓
ImageGenerationWorker(temp_outline)
       ↓
Worker emits: scene_image_ready(scene_idx=2, img_data)
       ↓
✅ Image saved to correct scene: cache["scene_images"][2]
       ↓
✅ Scene 2 card updated with new image
       ↓
✅ Other scenes unchanged
```

### Video Generation Flow

```
User clicks "🎬 Tạo Video" on Scene 2
       ↓
Signal: generate_video_requested(scene_idx=2)
       ↓
✅ _on_scene_generate_video(scene_idx=2)
       ↓
Validate scene has image
       ↓
Find scene where scene.index == 2
       ↓
Extract video_prompt from scene_2_data
       ↓
Create payload with:
  - title: "MyProject_scene2"
  - scenes: [{"prompt": video_prompt, "aspect": aspect_ratio}]
       ↓
VideoGenerationWorker(payload)
       ↓
Worker generates video
       ↓
✅ Video saved as: MyProject_scene2.mp4
       ↓
Worker emits: scene_completed(scene=1, path="MyProject_scene2.mp4")
       ↓
Callback: _on_single_scene_video_completed(scene_idx=2, path)
       ↓
✅ Log: "✓ Hoàn tất tạo video cảnh 2: MyProject_scene2.mp4"
       ↓
✅ Auto-download if enabled
```

## Scene Index Tracking

### Before: Scene Index Could Get Mixed Up ❌

```
Scenes:
  [0] → {index: 1} → Scene 1
  [1] → {index: 2} → Scene 2
  [2] → {index: 3} → Scene 3

Array-based processing (wrong):
  Process scenes[1] → Might save as scene_1.mp4 (array index)
  ❌ Scene 2 video saved as scene_1.mp4
```

### After: Proper Scene Index Matching ✅

```
Scenes:
  [0] → {index: 1} → Scene 1
  [1] → {index: 2} → Scene 2
  [2] → {index: 3} → Scene 3

Index-based processing (correct):
  Find scene where scene["index"] == 2
  Save as: "MyProject_scene2.mp4"
  ✅ Scene 2 video correctly saved
```

## Worker Isolation

### Before: Risk of Processing Multiple Scenes ❌

```
outline = {
  "scenes": [scene_1, scene_2, scene_3, ...]
}
       ↓
Worker processes all scenes
       ↓
❌ Risk of scene index mix-up
```

### After: Single Scene Processing ✅

```
Target: scene_idx = 2
       ↓
target_scene = find_scene_by_index(2)
       ↓
temp_outline = {"scenes": [target_scene]}
       ↓
Worker processes ONLY scene_2
       ↓
✅ No risk of cross-contamination
```

## Filename Strategy

### Before: Generic Filenames ❌

```
Video generated for Scene 2
       ↓
Saved as: "MyProject.mp4"
       ↓
Video generated for Scene 3
       ↓
❌ Overwrites: "MyProject.mp4"
       ↓
❌ Scene 2's video lost
```

### After: Scene-Specific Filenames ✅

```
Video generated for Scene 2
       ↓
title = f"{project_name}_scene{scene_idx}"
       ↓
✅ Saved as: "MyProject_scene2.mp4"
       ↓
Video generated for Scene 3
       ↓
✅ Saved as: "MyProject_scene3.mp4"
       ↓
Video regenerated for Scene 2
       ↓
✅ Overwrites: "MyProject_scene2.mp4" (correct file)
       ↓
✅ All scene videos preserved
```

## Signal Connection Pattern

### Before: Signals Not Connected ❌

```
SceneResultCard
  ├── Signal: recreate_requested ❌ → (nothing)
  └── Signal: generate_video_requested ❌ → (nothing)

VideoBanHangPanel
  ├── No handler for recreate
  └── No handler for generate_video
```

### After: Proper Signal Connections ✅

```
SceneResultCard
  ├── Signal: recreate_requested ✅
  │        ↓
  │        connect to: _on_scene_recreate_image(scene_idx)
  │
  └── Signal: generate_video_requested ✅
           ↓
           connect to: _on_scene_generate_video(scene_idx)

VideoBanHangPanel
  ├── ✅ _on_scene_recreate_image(scene_idx)
  │      - Finds correct scene by index
  │      - Creates isolated worker
  │      - Regenerates only that scene's image
  │
  └── ✅ _on_scene_generate_video(scene_idx)
         - Validates scene has image
         - Creates scene-specific payload
         - Tracks scene_idx in filename
         - Prevents cross-scene issues
```

## Testing Scenarios

### Scenario 1: Regenerate Middle Scene ✅

```
Initial state:
  Scene 1: ✅ image + ✅ video
  Scene 2: ✅ image + ✅ video
  Scene 3: ✅ image + ✅ video

Action: Click "🔄 Tạo lại" on Scene 2
       ↓
Result:
  Scene 1: ✅ unchanged
  Scene 2: ✅ NEW image generated
  Scene 3: ✅ unchanged

✅ Only Scene 2 regenerated, others untouched
```

### Scenario 2: Generate Video for Scene Without Affecting Others ✅

```
Initial state:
  Scene 1: ✅ video (MyProject_scene1.mp4)
  Scene 2: ❌ no video yet
  Scene 3: ✅ video (MyProject_scene3.mp4)

Action: Click "🎬 Tạo Video" on Scene 2
       ↓
Result:
  Scene 1: ✅ video unchanged (MyProject_scene1.mp4)
  Scene 2: ✅ NEW video (MyProject_scene2.mp4)
  Scene 3: ✅ video unchanged (MyProject_scene3.mp4)

✅ Scene 2 video created without affecting others
```

### Scenario 3: Retry Failed Scene ✅

```
Initial state:
  Scene 1: ✅ video (MyProject_scene1.mp4)
  Scene 2: ❌ video generation failed
  Scene 3: ✅ video (MyProject_scene3.mp4)

Action: Click "🎬 Tạo Video" on Scene 2 (retry)
       ↓
Process:
  1. Find scene where index == 2 ✅
  2. Create payload with title "MyProject_scene2" ✅
  3. Generate video ✅
  4. Save as MyProject_scene2.mp4 ✅
       ↓
Result:
  Scene 1: ✅ video unchanged (MyProject_scene1.mp4)
  Scene 2: ✅ NEW video (MyProject_scene2.mp4)
  Scene 3: ✅ video unchanged (MyProject_scene3.mp4)

✅ Retry successful, correct scene, no cross-contamination
```

## Code Components

### Key Data Structures

```python
# Scene data structure
scene = {
    "index": 2,                    # ✅ Used for matching
    "prompt_image": "...",          # For image generation
    "prompt_video": "...",          # For video generation
    "description": "...",
    "speech": "..."
}

# Cache structure
self.cache = {
    "outline": {
        "scenes": [scene_1, scene_2, scene_3, ...]
    },
    "scene_images": {
        1: "/path/to/scene_1.png",
        2: "/path/to/scene_2.png",  # ✅ Keyed by scene index
        3: "/path/to/scene_3.png",
    }
}

# Video worker payload
payload = {
    "scenes": [{                    # ✅ Only target scene
        "prompt": video_prompt,
        "aspect": aspect_api
    }],
    "title": f"{project_name}_scene{scene_idx}",  # ✅ Scene in filename
    "dir_videos": "/path/to/videos",
    "copies": 1
}
```

### Key Functions

```python
# 1. Signal connection
def _build_scene_cards(self, scenes):
    card = SceneResultCard(scene_idx, scene)
    card.recreate_requested.connect(self._on_scene_recreate_image)
    card.generate_video_requested.connect(self._on_scene_generate_video)

# 2. Scene lookup
def find_scene_by_index(self, scene_idx):
    for scene in self.cache["outline"]["scenes"]:
        if scene.get("index") == scene_idx:
            return scene
    return None

# 3. Image regeneration
def _on_scene_recreate_image(self, scene_idx):
    target_scene = find_scene_by_index(scene_idx)
    temp_outline = {"scenes": [target_scene]}
    worker = ImageGenerationWorker(temp_outline, ...)

# 4. Video generation
def _on_scene_generate_video(self, scene_idx):
    target_scene = find_scene_by_index(scene_idx)
    payload = {
        "title": f"{project_name}_scene{scene_idx}",
        "scenes": [{"prompt": target_scene["prompt_video"], ...}]
    }
    worker = VideoGenerationWorker(payload)
```

## Summary

### Problems Solved ✅

1. ✅ **Scene retry bug fixed**: Videos now go to correct scene
2. ✅ **Regenerate buttons work**: Both image and video regeneration functional
3. ✅ **Scene index tracking**: Properly maintained throughout process
4. ✅ **No cross-contamination**: Each scene processed independently
5. ✅ **Safe filenames**: Scene number in filename prevents overwrites

### Key Design Principles

1. **Scene Index Matching**: Always find scene by `scene["index"] == scene_idx`
2. **Worker Isolation**: Each regeneration processes only target scene
3. **Filename Strategy**: Include scene_idx in all filenames
4. **Signal Closure**: Capture scene_idx in lambda for callbacks
5. **Validation First**: Check prerequisites before processing

---

**This visual guide complements**: `docs/VIDEO_BAN_HANG_SCENE_FIX.md`
