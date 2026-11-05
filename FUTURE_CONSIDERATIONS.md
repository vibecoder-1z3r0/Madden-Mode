# Future considerations

Ideas we talked about but have not built. None of these is a commitment, and
the notes are starting points, not designs.

## Draw over a region

Drag a rectangle once, and the overlay covers only that area.

- **Why:** some things worth drawing over are not a window of their own, such
  as one part of the screen or a video inside another app. Pinning to a window
  does not help there, and a whole monitor is more than you want.
- **How it differs from pinning:** a region never follows anything. It stays
  put until you change it.
- **Saving it:** unlike a window handle, a region (a rectangle plus which
  monitor it is on) still makes sense after a restart, so it could be saved in
  the settings. It needs a fallback if that monitor is gone.
- **Picking it:** a translucent selector over the chosen monitor with a
  crosshair; drag to select, `Esc` cancels. A "Region..." entry next to
  "Target" in the toolbar and tray.
- **Testing:** the rectangle maths (normalizing a drag in any direction,
  clamping to the monitor, a minimum size) is plain logic. The selector can be
  tested offscreen.

## Choosing and pinning windows

- **Click to pick a window,** instead of choosing from a list. The list is
  simpler and more dependable; clicking is quicker. It needs a temporary
  full-screen "pick" mode.
- **Stack only above the pinned window.** Today the overlay is always on top, so
  it also covers any other window that overlaps the pinned window's area. A
  smarter version would sit just above the target window in the stacking order
  (on Windows, by placing it right after that window with `SetWindowPos`), which
  needs care so it does not fight the toolbar and toast.
- **Remember the pinned window across restarts,** by matching its title or
  program name. Window handles do not survive a restart, so today only the
  monitor is saved.
- **Rescale strokes when the pinned window is resized.** Today strokes keep
  their pixel position from the window's top-left corner and are not scaled.
- **Mixed-scaling monitors.** The conversion from Windows' physical pixels to
  Qt's logical pixels assumes Qt keeps each screen's origin fixed and scales
  only its size. That is exact at 100% scaling and unverified on mixed-scaling
  setups.

## Where the overlay can draw

- **All monitors at once,** as one overlay spanning every screen.
- **True fullscreen (exclusive) games.** Many block overlays. Borderless or
  windowed is the supported case; fullscreen would be best-effort at most.
- **macOS.** CI now runs the tests and a startup check there, and key names are
  shown as Cmd and Option, but nothing has been tried on a Mac. What is still
  missing, all of which needs a Mac to build and verify:
  - **Global hotkeys.** A backend for the Mac's system-wide hotkey API, plus the
    permission prompts macOS shows for apps that watch the keyboard.
  - **Window pinning.** Listing and following other apps' windows through the
    macOS window list.
  - **Fullscreen apps.** A macOS fullscreen app lives in its own Space, and an
    overlay does not show over it unless its window is marked to join all
    Spaces.
  - **Click-through.** The Qt flag used today is the method that proved
    unreliable on Windows, so it needs checking on a Mac.
  - **Menu bar and Dock.** The tray icon should be a monochrome template image
    for the menu bar, and the app probably should not show a Dock icon.
- **Linux.** Same gaps as macOS for hotkeys and window pinning; Wayland restricts
  both heavily.

## Drawing

- **Shapes** (arrows, circles, lines) on top of freehand.
- **Pressure-sensitive width** for styluses. Each point already carries a
  pressure value (always 1.0 for now), so the stroke format will not change.

## Starting state

- **Remember the last pen and color between sessions.** The app always starts
  on the comet in yellow today. Saving the last choice would mean storing which
  pen and color were active in the settings file.
- **Per-pen colors.** A picked color currently applies to whichever pen you use,
  so pens lose their own color once you pick one. Giving each pen its own
  remembered color is an alternative.

## Studio mode

A "live feed" of the screen you can pause, rewind and fast forward, then
telestrate over. It needs a rolling screen-capture buffer. Strokes would be
stored with timestamps, separate from the picture, so a mark made at 2:14 of the
buffer replays when you rewind, and a timeline could show where the strokes are.
Overlay mode keeps no history, by design.

## Housekeeping

- **Pin the Python version in CI** so the runners and your machine agree. The
  project allows 3.13 and newer, and the Windows runner used a newer version
  than the one we developed on.
- **Measure performance at 4K.** The renderer allocates a layer per stroke per
  frame, which has not been profiled.
- **A packaged installer.** That would also mean shipping the Qt licence
  notices; see `ARCHITECTURE.md`.
