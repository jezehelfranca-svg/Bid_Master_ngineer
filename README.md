# ⚡ Antigravity — Telecom Material Takeoff Tool

**A high-performance, client-side material takeoff (MTO) and estimation suite designed specifically for telecommunications and security systems design.**

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Application Layout & Navigation](#application-layout--navigation)
- [Step-by-Step User Guide](#step-by-step-user-guide)
  - [1. Launching the App](#1-launching-the-app)
  - [2. Loading Drawings](#2-loading-drawings)
  - [3. Calibrating the Scale](#3-calibrating-the-scale)
  - [4. Creating & Configuring Materials](#4-creating--configuring-materials)
  - [5. Coverage Studies (PAGA & CCTV)](#5-coverage-studies-paga--cctv)
  - [6. Performing the Takeoff](#6-performing-the-takeoff)
  - [7. Exporting Reports & Drawings](#7-exporting-reports--drawings)
- [Keyboard Shortcuts & Hotkeys](#keyboard-shortcuts--hotkeys)
- [Engineering Calculations](#engineering-calculations)
  - [Parabolic Sag Deflection (Aerial Cables)](#parabolic-sag-deflection-aerial-cables)
  - [Linear Takeoff Formula](#linear-takeoff-formula)
  - [PAGA Sound Radius Calculation](#paga-sound-radius-calculation)
  - [CCTV Field-of-View Calculation](#cctv-field-of-view-calculation)
- [Technology Stack](#technology-stack)
- [Developer & File Structure](#developer--file-structure)

---

## Overview

**Antigravity Telecom MTO** is an installation-free, single-file browser application built to accelerate the material quantification process on telecom floor plans, site layouts, and CAD drafts. Designed for engineers, estimators, and project leads, this tool handles complex mathematical adjustments—such as service loop slack, cable waste, and aerial span sag—entirely client-side. Your drawing files and project records remain locally stored and private.

---

## Key Features

- **Multi-Format Drawing Loader**: Support for vector PDFs (multi-page rendering via PDF.js) and standard image files (PNG, JPG, BMP, WebP).
- **Dual-Method Calibration**: Calibrate using drawing ratios (e.g., 1:100, 1:250) or interactively draw a reference line over a known dimension.
- **Telecom Asset Palette**: Out-of-the-box TIA/EIA-606 layer presets (ISP cabling, OSP cabling, outlets, WAPs, cabinets) or create custom materials.
- **Linear & Counter Takeoffs**: Draw multi-segment polyline cable/conduit runs, or place equipment count markers.
- **Equipment Symbols**: Canvas-drawn symbols (WiFi APs, RJ45 wall outlets, cabinets, cameras, speakers, manholes) that scale dynamically.
- **Signal Coverage Visualizers**: Instantly overlay sound propagation zones (PAGA speakers) or field-of-view wedges (CCTV cameras) on your drawing.
- **Orthographic Mode**: Restrict drawing segments to horizontal or vertical axes (F8 lock) for precise pathways.
- **CAD-like Controls**: Dynamic zooming, panning, snap-to-points, node removal, and keyboard shortcuts.
- **Robust Import/Export**: Save and load complete project states (JSON), share material configurations (JSON), export procurement-ready CSV sheets, and download marked-up layouts as PNGs or PDFs.

---

## Application Layout & Navigation

The interface is divided into four main functional areas:

1. **Top Header**: Displays the application branding and current calibration scale indicator.
2. **Left Control Sidebar**: Includes drawing loading tools, the interactive Material Palette, custom material builder, and project saving/loading options. Can be pinned or unpinned.
3. **Workspace Canvas**: The primary viewport. Contains the floating tool dock, canvas zoom buttons, and the dual-layer rendering canvas.
4. **Bottom Takeoff Table**: Displays a live-updated summary of all materials, counts, raw measurements, applied engineering modifiers, and total procurement quantities.

### Interface Tips
- **Toggle Sidebar**: Click the sidebar collapse button or press `Ctrl + B`.
- **Toggle Bottom Panel**: Click the bottom table collapse button or press `Ctrl + J`.
- **Sidebar Auto-Hide**: Unpin the sidebar to float it. When unpinned, hovering over the left edge of the screen slides it open, and moving your cursor away automatically hides it after 400ms.
- **Zoom & Pan**: Use the zoom buttons (+, -, fit) on the right side of the canvas, or hold `Ctrl` and scroll your mouse wheel. In Pan mode, click and drag the canvas to move.

---

## Step-by-Step User Guide

### 1. Launching the App
Open the [takeoff_tool.html](takeoff_tool.html) file directly in any modern web browser (Google Chrome, Microsoft Edge, Mozilla Firefox, or Apple Safari). No web server, dependencies, or command line inputs are necessary.

### 2. Loading Drawings
- Under the **Drawing Sources** section in the sidebar, click **Load PDF, Image or CAD**.
- Select a local drawing file:
  - **PDF**: The app will render the document. Use the navigation controls at the bottom of the screen to change pages.
  - **Image**: Renders the picture immediately.
- Once loaded, the empty workspace state hides, and the canvas zoom resets to fit.

### 3. Calibrate the Scale
Before measuring, you must calibrate the drawing to translate pixels to real-world dimensions (meters or feet):
- **Scale Ratio**: Enter a title-block scale (e.g., `1:100` or `1:250`), select the unit (e.g., `m` or `ft`), and click **Set Ratio Scale**.
- **Interactive Reference**:
  1. Click **Draw Reference Line** inside the Calibration modal.
  2. Select a dimension line on the plan (e.g., door width, room length). Click once to start, and click again to end the line.
  3. Enter the real-world distance and unit, then click **Apply Calibration**.
- The scale indicator at the top right will update to display the calibrated scale.

### 4. Creating & Configuring Materials
Manage your takeoff categories in the **Material Palette**:
- To add a material, click **Create Material** to open the config modal.
- Choose a name, color, TIA/EIA layer, and takeoff type:
  - **Linear Run**: For cables, conduits, and trays.
    - *Modifiers*: Add waste percentage (e.g., `10%`) and fixed service loops (e.g., `3.0m` per run).
    - *Aerial Sag*: Check "Is Aerial Cable" to compute parabolic sag. Define the weight per unit length ($w$ kg/m) and span tension ($T$ kg).
  - **Counter Pin**: For endpoints like cameras, outlets, and APs.
    - *Modifiers*: Add service loop slack or vertical conduit drops.
    - *Equipment Symbol*: Choose a representation symbol (WAP, RJ45 Outlet, Cabinet, CCTV, PAGA, etc.).

### 5. Coverage Studies (PAGA & CCTV)
Set up visual calculation layers for counter-pin equipment:
- **PAGA Speakers**: Select "PAGA Sound Study" in the coverage type menu. Input speaker sensitivity (dB at 1W/1m), amplifier power tap (Watts), ambient noise level (dBA), and target signal-to-noise margin (usually 10 or 15 dB). The tool will project the maximum acoustic boundary radius.
- **CCTV Cameras**: Select "CCTV Camera Study" in the coverage type menu. Enter the camera's Horizontal Field of View (HFOV) or pick a lens focal length preset (e.g., 2.8mm, 4mm, 6mm, 12mm). Define range distances for DORI standard metrics (Detection, Observation, Recognition, Identification). A shaded FOV wedge will project on the canvas.

### 6. Performing the Takeoff
Select a material from the sidebar palette. The application will switch to the correct tool mode:
- **Linear Tool (l)**: Click on the canvas to place path vertices. Press `F8` to toggle Orthographic drawing constraints. Press `Ctrl + Z` or `Backspace`/`Delete` to undo the last node. Double-click or press `Enter`/`Space` to finish the path.
- **Counter Tool (c)**: Click to place markers. If coverage is enabled, the boundary circles/wedges will automatically project.
- **Select Tool (v)**: Click and drag placed points or paths to adjust their position. Select an item and press `Delete` or `Backspace` to remove it.
- **Delete Tool (d)**: Hover over placed markers or paths and click to delete them instantly.

### 7. Exporting Reports & Drawings
- **Save Project Session**: Click **Save Project State (JSON)** to download the workspace data. You can re-upload this file later using **Load Project State** to resume your estimating session.
- **Save Material Templates**: Click **Export Configuration** to download the custom material catalog, or click **Import Configuration** to load standard presets.
- **Get Quantities Report**: Click **Export Takeoff to CSV** in the bottom panel to generate a spreadsheet detailing raw counts, modifiers, total physical measurements, and computed coverage coverage areas.
- **Export Markup Layout**: Click **Export Marked-Up Drawing** and choose **PNG** or **PDF** to download a high-resolution export containing your drawings and takeoff annotations.

---

## Keyboard Shortcuts & Hotkeys

Use these shortcuts to work efficiently inside the workspace:

| Key Command | Action |
|-------------|--------|
| **`h`** | Switch to **Pan/Hand** Mode |
| **`v`** | Switch to **Select/Move** Mode |
| **`c`** | Switch to **Counter/Point** Mode |
| **`l`** | Switch to **Linear/Path** Mode |
| **`d`** | Switch to **Delete** Mode |
| **`F8`** | Toggle **Ortho Mode** (forces 90-degree lines) |
| **`Ctrl + B`** | Toggle **Sidebar** panel display |
| **`Ctrl + J`** | Toggle **Bottom Takeoff** panel display |
| **`Ctrl + Scroll`** | Zoom canvas viewport in and out |
| **`Ctrl + Z`** | Undo last placed point or takeoff item |
| **`Backspace` / `Delete`** | Delete last node (during drawing) or selected item (Select Mode) |
| **`Enter` / `Space`** | Finish drawing active path |
| **`Esc`** | Cancel active drawing path / clear selection / return to Pan Mode |

---

## Engineering Calculations

### Parabolic Sag Deflection (Aerial Cables)
To estimate the physical sag of cables strung between poles or supports, the software utilizes a parabolic catenary approximation formula to add length modifiers:

$$S = L \cdot \left(1 + \frac{w^2 \cdot L^2}{24 \cdot T^2}\right)$$

*Where:*
- $S$: Actual sag-adjusted physical cable length (meters/feet).
- $L$: Measured horizontal line span length (meters/feet).
- $w$: Unit weight of the cable (kilograms per meter / lbs per foot).
- $T$: Horizontal cable tension (kilograms/pounds force).

### Linear Takeoff Formula
The total bill of materials length ($L_{total}$) for linear runs combines sag, waste percentage, and physical slack loops:

$$L_{total} = S \cdot \left(1 + \frac{\text{waste}\%}{100}\right) + \text{slack}$$

- For standard flat conduits and cable trays, $S$ defaults directly to the horizontal measured length.

### PAGA Sound Radius Calculation
Acoustic coverage projections are modeled using the Inverse Square Law of sound attenuation, assuming free-field hemispherical propagation:

$$\text{SPL}_{r} = \text{Sensitivity} + 10\log_{10}(\text{Power}) - 20\log_{10}(r)$$

*Solving for $r$ (radius in meters):*

$$r = 10^{\frac{\text{Sensitivity} + 10\log_{10}(\text{Power}) - (\text{Ambient Noise} + \text{Target Margin})}{20}}$$

- *Indoor Attenuation*: When selected, the formula adds a $-3\text{ dB}$ room propagation penalty to account for standard structural absorption.

### CCTV Field-of-View Calculation
Camera wedge angles are mapped to the Horizontal Field of View ($HFOV$), calculated based on the image sensor size and lens focal length:

$$HFOV = 2 \cdot \arctan\left(\frac{W}{2 \cdot f}\right) \cdot \frac{180}{\pi}$$

*Where:*
- $W$: Width of the camera's image sensor (typically $4.8\text{ mm}$ for 1/3" sensors).
- $f$: Lens focal length in millimeters (e.g., $2.8\text{ mm}$, $4\text{ mm}$, $6\text{ mm}$).

---

## Technology Stack

- **Client Logic**: Vanilla JavaScript (ES6+), running entirely in the browser thread.
- **Rendering Layer**: Double-buffered HTML5 Canvas 2D API (canvas background + active drawing foreground).
- **Styling**: Modern CSS3 using custom HSL/RGB design variables, featuring a custom dark theme and transition animations.
- **External Dependencies (CDN)**:
  - [PDF.js](https://mozilla.github.io/pdf.js/) for high-fidelity multi-page PDF rendering.
  - [jsPDF](https://github.com/parallax/jsPDF) for client-side print-ready PDF creation.
  - [FontAwesome 6.4](https://fontawesome.com/) for interface symbols.

---

## Developer & File Structure

```
TELE/
├── takeoff_tool.html         # Main application file (all markup, styles, and script logic)
├── README.md                 # System user guide and specifications
├── annotate_pdf.py           # Backend PDF markup processor
├── bom_vendor_comparison.py  # Excel utility comparing bills of materials against vendor quotes
└── extracted_project_content.txt # Source project specification notes
```
