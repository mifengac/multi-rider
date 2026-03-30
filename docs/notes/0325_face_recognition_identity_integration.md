# Face Recognition Identity Integration Checklist

## 1. Goal

- Add an identity recognition workflow to both the current local upload detection flow and the Oracle detection flow.
- Keep the existing detection capability unchanged: users still upload ZIP images or videos, run detection, and get filtered results.
- After detection is complete, allow users to select one or more images from the filtered result set and run face identity recognition.
- Reuse the existing approach in `service/0312face_recognition_pipeline.py` as the technical baseline.
- Use the previously designed intranet SQL as the face library source of truth.

## 2. Current Project Baseline

- The current local upload feature already supports ZIP image packages and video files, then writes matched images or frames into a downloadable ZIP.
- The upload entry point is `routes/upload_routes.py`.
- The background upload job logic is `service/upload_job_service.py`.
- The current local upload page is in `templates/index.html`.
- The existing standalone face recognition reference is `service/0312face_recognition_pipeline.py`.

## 3. Target User Flow

1. User runs detection from either the Oracle detection tab or the existing local upload tab.
2. The system completes object detection and generates a filtered result set.
3. The page shows the result gallery instead of only showing downloadable files.
4. User selects one or more result images.
5. User clicks `Identify Face` or `Identify Selected`.
6. The backend detects one or more faces in each selected image.
7. The backend compares the face embeddings with the cached face feature library.
8. The page shows per-image top matches, similarity scores, face quality hints, and a clear `matched / no match / low quality / no face` status.

## 4. Scope

### In Scope

- Face identity recognition for filtered local-upload results.
- Face identity recognition for filtered Oracle detection results.
- One-time or scheduled synchronization of the personnel face library from the intranet SQL source.
- Local cache of decoded face photos and embeddings.
- Single-select and multi-select result image recognition in the web UI.
- Basic administration actions for rebuilding or refreshing the face library.

### Out of Scope for First Version

- Multi-user permission system.
- Face search across the full raw upload set before object detection.
- Automatic identity recognition for every filtered image in the background.
- Figma-to-code automation.

## 5. Figma Design Deliverables

### 5.1 Page Structure

- Keep both `Oracle Detection` and `Local Upload Detection` as identity-recognition entry points.
- Add a post-detection `Result Review` area on the right side or below the progress panel.
- Add an `Identity Recognition` drawer or modal for selected images.

### 5.2 Required Screens

- Upload page default state.
- Detection running state.
- Detection complete state with multi-select result gallery.
- Single result image detail view.
- Batch identity recognition state for multiple selected images.
- Identity recognition panel with:
  - selected image preview
  - detected face thumbnails
  - face quality badges
  - top-5 identity candidates
  - similarity scores
  - final decision status
- Empty state: no face detected.
- Empty state: no match above threshold.
- Error state: face library not built.
- Admin state: face library sync and rebuild progress.

### 5.3 Key Components

- Result image card with checkbox, thumbnail, source file name, detect model tag, and `Identify Face` action.
- Batch toolbar with selected count, `Identify Selected`, `Clear Selection`, and progress hint.
- Face candidate card with name, ID number, similarity score, and source photo thumbnail.
- Face status chips:
  - `Matched`
  - `No Match`
  - `No Face`
  - `Low Quality`
  - `Multiple Faces`
- Admin panel cards:
  - `Sync from SQL`
  - `Rebuild Embeddings`
  - `Last Sync Time`
  - `Valid Records`

### 5.4 Design Notes

- Reuse the current visual language in `templates/index.html` instead of introducing a new design system.
- Prefer a drawer or side panel for identity results so the user can keep the detection context visible.
- Optimize for evidence review: large preview, concise metadata, clear status hierarchy, and copyable identity fields.

## 6. Backend Architecture Plan

### 6.1 New Service Modules

- `service/face_identity_service.py`
  - load face models
  - run face detection and face embedding extraction
  - run 1:1 and 1:N matching
- `service/face_library_service.py`
  - sync personnel data from intranet SQL
  - decode and save personnel photos
  - build and reload local face embeddings
  - manage cache metadata
- `service/face_result_service.py`
  - bind Oracle and local-upload result images to later face-identification actions
  - persist recognition outputs if needed

### 6.2 Reuse From `0312face_recognition_pipeline.py`

- `FaceDetector`
- `FaceRecognizer`
- `extract_probe_embeddings()`
- `search_face()`
- `verify_face()`
- ONNX dynamic output patch logic for SCRFD
- gallery cache layout:
  - `face_data/photos`
  - `face_data/features`
  - `face_data/person_db.pkl`

### 6.3 Refactor Guidance

- Do not keep all logic only in one script.
- Split reusable model and matching logic out of the standalone pipeline file.
- Convert script-style workflow into app services with logging, config support, and API-safe return objects.

## 7. Face Library Strategy

### 7.1 Data Source

- Keep the face library source in the intranet SQL system.
- Reuse the previously designed SQL from `0312face_recognition_pipeline.py`.
- Keep SQL definition configurable in the app instead of hardcoding credentials in service code.

### 7.2 Local Cache

- Save decoded face photos locally.
- Save one embedding file per person.
- Save a serialized person index for fast startup.
- Add a small cache metadata file with:
  - last sync timestamp
  - source row count
  - valid photo count
  - valid embedding count
  - model versions

### 7.3 Refresh Modes

- Full sync from SQL.
- Rebuild embeddings without requerying SQL.
- Optional incremental refresh later.

## 8. API Plan

### 8.1 New Routes

- `POST /face-library/sync`
  - sync face records from intranet SQL
- `POST /face-library/rebuild`
  - rebuild embeddings from local face photos
- `GET /face-library/status`
  - return last sync time, valid counts, and model readiness
- `POST /face/identify`
  - input: one or more selected result image references
  - output: detected faces and top matches for each selected image
- `POST /face/identify/batch`
  - optional dedicated batch endpoint if the payload becomes too large for a single identify API
- `POST /face/verify`
  - optional future API for one specific ID check

### 8.2 Input Strategy

- Avoid uploading the same image again for identity recognition.
- Reuse the already generated result image path after detection is done.
- Support both Oracle result assets and local-upload result assets.
- Store result image metadata so the page can request identity recognition by image ID or path token.

### 8.3 Output Contract

- `status`: `matched | no_match | no_face | low_quality | error`
- `face_count`
- `faces[]`
  - `bbox`
  - `blur_score`
  - `det_score`
  - `used_align`
  - `top_matches[]`
    - `name`
    - `id_number`
    - `score`
    - `photo_path`

## 9. Frontend Integration Plan

### 9.1 Existing Page Changes

- Extend both Oracle and local-upload completion states to show a result gallery.
- Add result image cards for both ZIP image hits and kept video frames.
- Add a selected-image preview area and batch selection summary.
- Add an `Identify Face` button per image card and an `Identify Selected` batch action.

### 9.2 New UI Behaviors

- After detection completes, fetch and render result assets.
- Let the user select one or more images for identity recognition.
- Show identity recognition progress per image and for the full batch.
- Render top candidate identities with confidence score and face crop preview.
- Clearly show when the image contains:
  - no face
  - multiple faces
  - low-quality face
  - no confident match

### 9.3 Frontend Files to Update

- `templates/index.html`
- optional split JS file if the inline page script becomes too large
- optional new preview asset endpoints

## 10. Storage and Result Management

- Save filtered output images in a browsable directory, not only in a ZIP package.
- Keep a lightweight manifest per upload job:
  - job ID
  - source type
  - image file names
  - local image paths
  - thumbnail paths if generated
  - later face recognition results
- Consider storing this manifest in SQLite next to the current job tracking data.

## 11. Model and Runtime Requirements

### 11.1 Required Models

- SCRFD face detector ONNX
- ArcFace recognition ONNX

### 11.2 Config Items

- `FACE_MODEL_DET`
- `FACE_MODEL_REC`
- `FACE_DATA_DIR`
- `FACE_SIMILARITY_THR`
- `FACE_BLUR_THRESH`
- `FACE_SQL_ENABLED`
- `FACE_SQL_HOST`
- `FACE_SQL_PORT`
- `FACE_SQL_DB`
- `FACE_SQL_USER`
- `FACE_SQL_PASSWORD`
- `FACE_SQL_QUERY_PATH` or inline SQL config

### 11.3 Environment Notes

- The SQL source is intranet-only, so the sync feature must fail gracefully when the app is outside the intranet.
- The face library should remain usable from the local cache even when SQL is temporarily unreachable.

## 12. Security and Compliance Checklist

- Avoid exposing raw SQL credentials in Git-tracked files.
- Do not return full sensitive identity fields unless required by the user role.
- Add audit logging for:
  - library sync
  - rebuild
  - face identify requests
- Add retention rules for cached result images and face match outputs.

## 13. Development Checklist

### 13.1 Product and UX

- [ ] Confirm the first-version workflow is `detect first, identify second`.
- [ ] Confirm whether the identity result should show top-1 only or top-5.
- [ ] Confirm whether multiple faces in one image should all be matched or only the largest face.
- [ ] Confirm the batch-selection upper limit per recognition request.
- [ ] Produce Figma screens for upload result gallery and identity side panel.

### 13.2 Backend Foundation

- [ ] Extract reusable face model code from `service/0312face_recognition_pipeline.py`.
- [ ] Create `face_identity_service.py`.
- [ ] Create `face_library_service.py`.
- [ ] Move hardcoded config to `config.py` and `app.env`.
- [ ] Standardize API-safe response schemas.

### 13.3 Face Library

- [ ] Add SQL sync service using the existing intranet SQL.
- [ ] Save decoded personnel photos locally.
- [ ] Build embeddings and serialized cache.
- [ ] Add status API for cache readiness.
- [ ] Add rebuild API for embedding refresh without SQL requery.

### 13.4 Upload Result Binding

- [ ] Persist filtered upload result images in a stable local directory.
- [ ] Persist filtered Oracle result images in a stable local directory.
- [ ] Add result manifest metadata.
- [ ] Expose result list API for the frontend.
- [ ] Support both image ZIP hits and video frame hits.

### 13.5 Face Recognition APIs

- [ ] Add `POST /face/identify` with multi-image payload support.
- [ ] Add `POST /face/identify/batch` if batch execution needs a separate endpoint.
- [ ] Add `GET /face-library/status`.
- [ ] Add `POST /face-library/sync`.
- [ ] Add `POST /face-library/rebuild`.
- [ ] Add error handling for `no face`, `no match`, and `library unavailable`.

### 13.6 Frontend

- [ ] Render post-detection gallery in both Oracle and local-upload pages.
- [ ] Add selected-image preview and selected-count summary.
- [ ] Add `Identify Face` and `Identify Selected` actions.
- [ ] Show recognition progress, batch progress, and errors.
- [ ] Render face match cards and quality hints.
- [ ] Add admin controls for sync and rebuild if required.

### 13.7 Testing

- [ ] Unit test face service output formats.
- [ ] Integration test with cached local face library only.
- [ ] Integration test with intranet SQL available.
- [ ] Test `no face`, `multiple faces`, `blurred face`, and `no match` cases.
- [ ] Test large result sets from video frame outputs.

## 14. Acceptance Criteria

- User can complete object detection as before without regression.
- User can view filtered result images in the page without downloading files first.
- User can select one or more filtered images and trigger face identity recognition.
- The app returns top candidate identities with similarity scores.
- The app clearly reports `no face`, `low quality`, or `no match` when appropriate.
- The face library can be built from intranet SQL and reused from local cache offline.
- A rebuild workflow exists after face preprocessing or model changes.
- The same identity-recognition capability is available in both Oracle detection and local-upload detection flows.

## 15. Suggested Delivery Phases

### Phase 1

- Refactor `0312face_recognition_pipeline.py` into reusable services.
- Add local cache loading and manual identify API using existing result images.

### Phase 2

- Bind Oracle and local-upload result images to a unified gallery view.
- Add multi-select image recognition and identity side panel in the web UI.

### Phase 3

- Add face library sync and rebuild management.
- Add status page or admin card.

### Phase 4

- Optimize performance, error handling, and evidence-oriented UX.

## 16. Recommended First Implementation Order

1. Refactor face recognition logic into reusable backend services.
2. Unify Oracle and local-upload result assets into one browsable result abstraction.
3. Add multi-image `Identify Face` capability and render top matches.
4. Add intranet SQL sync and library rebuild workflow.
5. Polish UX and add admin operations.
