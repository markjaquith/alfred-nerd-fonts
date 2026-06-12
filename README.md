# Alfred Nerd Fonts

Search Nerd Font symbols in Alfred, choose one, and paste its UTF-8 character into the frontmost macOS app.

## Files

- `update-icons.py` downloads Nerd Fonts' generated CSS from the `gh-pages` branch and builds `data/nerd-font-glyphs.json`.
- `update-icons.py` also downloads `SymbolsNerdFontMono-Regular.ttf` and its license, which are used only for preview rendering.
- `render-icon.swift` renders cached PNG previews for Alfred result icons.
- `nerd-fonts-search.py` is the Alfred Script Filter. It reads the JSON index and returns Alfred items with cached preview icons.
- `icon.png` is the Alfred workflow icon. The editable source is `assets/workflow-icon.svg`.

## Refresh The Icon Index

```sh
/usr/bin/python3 update-icons.py
```

## Alfred Setup

1. Open Alfred Preferences.
2. Go to Workflows.
3. Click `+`, choose `Blank Workflow`, and name it `Nerd Fonts`.
4. Drag `icon.png` onto the workflow icon well if you want the custom `NF` icon.
5. Right-click the canvas and choose `Inputs` > `Script Filter`.
6. Set `Keyword` to `nf`.
7. Set `Argument` to `Optional`.
8. Set `Language` to `/bin/zsh`.
9. Set `with input as argv`.
10. Use this script, keeping the path as-is for this repo:

```sh
/usr/bin/python3 "/Users/mark.jaquith/Dev/alfred-nerd-fonts/nerd-fonts-search.py" "$1"
```

11. Save the Script Filter.
12. Right-click the canvas and choose `Outputs` > `Copy to Clipboard`.
13. Connect the Script Filter to Copy to Clipboard.
14. In Copy to Clipboard, set `Clipboard Contents` to `{query}`.
15. Enable `Automatically paste to front most app`.
16. Save.

Now invoke Alfred, type `nf leaf`, choose a result, and Alfred will paste the symbol.

The first search that returns new symbols may pause briefly while the Swift renderer compiles and PNG previews are cached in `icons/`. After that, previews are reused.

Hold `Cmd` while selecting a result to paste the Nerd Font class name instead. Hold `Option` while selecting to paste the Unicode codepoint.

## Font Note

Alfred results use rasterized PNG previews, so Alfred itself does not need to use a Nerd Font. The pasted symbols are still private-use Unicode characters. They only display correctly in target apps or fields using a Nerd Font, or when macOS can fall back to one. If pasted symbols look like boxes, install/use a Nerd Font such as `Symbols Nerd Font Mono` or set the target app to a Nerd Font.
