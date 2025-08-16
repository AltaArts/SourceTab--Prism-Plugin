# **Proxys**

<br>

One of the aims of SourceTab to to simplify the handling of Proxys by doing two main things:

**Discovery / Transfer:**  The plugin attemps to discover a video file's associated Proxy by searching adjacent directories (**see Proxy Search Templates below**).

**Generation:**  The plugin uses ffmpeg to generate new Proxy files using user defined Proxy Presets (**see FFMPEG Settings below**).



___

## **Functions Panel**

![Proxy Functs](DocsImages/proxy_functs.png)

Proxy handling is enabled by setting the Proxy checkbox in the SourceTab Functions panel.  The selected proxy mode and preset will be displayed for quick reference.  The cog button is used to configure the Proxy Settings.

<br>

## **Proxy Settings**

![Proxy Popup Overview](DocsImages/proxy_popup_overview.png)

This is the main configuration for Proxy handling, and is saved to the Project Settings (pipeline.json).  

<br>

### **Proxy Mode**

![Proxy Popup Mode](DocsImages/proxy_popup_mode.png)

This is the per-project Proxy handling mode:

- **Copy Proxys:** Only transfer Proxys that have been discovered by the plugin (noted by the "PXY" icon in the File Tile).  No new Proxys will be generated.

- **Generate Proxys:** Generate new Proxys for each transferred file, based on the FFMPEG Settings. No original proxys will be transferred.

- **Generate Missing Proxys:** Will transfer any discovered Proxys, or generate new Proxys for files without a discovered Proxy.


        Generate Missing Proxies is the suggested mode as it covers most cases, both if Source Proxys exist or not.

<br>

### **Global Proxy Settings**

![Proxy Popup Global](DocsImages/proxy_popup_global.png)

These are the Proxy directory settings.  These settings will apply to both transferred Proxys, as well as generated Proxys.  

- **Override Proxy Dir:**  This will override the resolved Proxy directory and save/generate proxys to this directory.  If left blank, the resolved directory will be used (if resolved).

- **Fallback Proxy Dir:**  This is the fallback directory used if the plugin is unable to resolve a proxy directory, and the Override is not utilized.  This should always be populated with a usable path to stop errors.

        NOTE: Both relative and absolute path formatting are allowed:

        - Relative: standard "dot notation" is utilized to build relative paths such as ./ (current directory) and ../ (parent directory)

        - Absolute:  standard filepath style with the full path such as "c:\path\to\dir" or "c:/path/to/dir"

<br>

### **Proxy Search Templates**

![Proxy Popup Search](DocsImages/proxy_popup_search.png)

- These are the path templates where the plugin will search to attempt to discover Proxy files.  Clicking the *Edit Proxy Search Templates* button will open the template editor to allow customization (**see Proxy Search Editor below**).

<br>

### **FFMPEG Settings**

![Proxy Popup ffmpeg](DocsImages/proxy_popup_ffmpeg.png)

- **Proxy Preset:** Select the Proxy Preset used for generation.

- **Proxy Scale:** The resulting generated Proxy resolution.  This scale is based on the original Source Mainfile resolution.

-  **Edit Proxy Settings:** Open the Preset Editor to configure the Proxy Presets (**see Proxy Preset Editor below**).

<br>

## **Proxy Search Editor**

![Proxy Search Overview](DocsImages/proxy_search_overview.png)

Proxy Search Templates that will be scanned to attempt to find a Mainfile's associated Proxy.  When a directory is selected in the Source Panel (left-side), all the files in that directory are loaded into File Tiles, and the plugin will use these templates to scan the paths/filenames for associated Proxys. The order of the templates are used for priority, and the scan will stop when a proxy is discovered (for each file).  This ignores the file-extension.

- **Edit:**  Enabled editing of the templates (the templates are normally read-only to avoid accidental edits).
- **Add:**  Add new entry to allow a new user-defined template.
- **Remove:** Delete the currently selected template.
- **Up/Down:** Move the selected template in the list.  The template list order is used 
- **Validate:**  Performs a quick sanity check for formatting and errors.
- **Reset to Defaults:**  Completly remove all current templates, and reset to the SourceTab defaults.  This will erase all custom templates added by the user.
- **Save:**  Any changes to the templates mucst be saved using this button (or choose Cancel to discard).


This uses relative paths based on the MainFile's directory, and uses standard dot-notation for relative directories:

    ./   - current directory
    ../  - parent directory

The search also uses placeholders to allow the search to find Proxys that have prefixes or suffixes:

@MAINFILEDIR@    @MAINFILENAME@

    Examples:

    - @MAINFILEDIR@\\proxy\\@MAINFILENAME@      -- search in a subdir named "proxy" with same name as the mainfile
    - @MAINFILEDIR@\\@MAINFILENAME@_proxy       -- search in the same dir with the mainfile name with a "_proxy" suffix
    - @MAINFILEDIR@\\..\\proxy\\@MAINFILENAME@" -- search in dir named "proxy" that is at the same level as the main dir




<br>

___
jump to:

[**Installation**](Doc-Installation.md)

[**Settings**](Doc-Settings.md)

[**Interface**](doc-Interface.md)

[**File Naming**](Doc-FileNaming.md)

[**Metadata Handling**](Doc-Metadata.md)