# CTF UI
An Electron/React/Typescript editor/runner for CTF test scripts.

## Table of Contents <!-- omit in toc -->
- [Building from Source](#Building-from-Source)
- [User's Guide](https://js-er-code.jsc.nasa.gov/aes/ctf_ui/wikis/user-guide)
- [Design Overview](#Design-Overview)
  - [Clean Architecture](#Clean-Architecture)
  - [Model-View-Presenter](#Model-View-Presenter)
  - [Editor Design](#Editor-Design)
  - [Drag and Drop](#Drag-and-Drop)
  - [Workspace File](#Workspace-File)
  - [Plugins](#Plugins)
  - [Vehicle Data](#Vehicle-Data)
- [Codebase Tour](#Codebase-Tour)
- [Build Tools](#Build-Tools)
  - [Babel](#Babel)
  - [Electron](#Electron)
  - [React](#React)
  - [Typescript](#Typescript)
  - [Webpack](#Webpack)
- [References](#References)
- [Known Issues](#Known-Issues)
- [Contact](#Contact)

## Building from Source
If you have not installed NodeJS/NPM, visit https://nodejs.org/en/ and install Node version >= 10.12.0 (tested with v12.5.0). NPM is included in the installation. 

```bash
# enter ctf-ui directory from ctf directory 
cd tools/ctf_ui/

# install the dependencies
sudo yum install libXScrnSaver-devel

npm install
# for production build and run
npm start
# once built, use the following for faster starts (skips the build)
npm run start:prod

# for development with hot-reloading
npm run serve
```

## User's Guide

Refer the the following [Wiki Page](../../docs/ctf_editor/usage_guide.md) for a tutorial on how to use the editor.

## Design Overview
The architecture of the GUI is based around a few key principles.

### Clean Architecture
Clean Architecture is a design pattern in which an application is separated into concentric layers. Each layer only depends on the layers inside (or below) it. The core layer defines model objects operated on by the app. The next layer contains use cases and business logic that manipulate these model objects. Finally, the application layer contains implementation specific UI frameworks, database code, etc. that provides the interfaces for triggering the domain-level business logic or rendering/storing the output. This approach enables domain-level business logic to be written independent of UI frameworks or other application-level libraries, meaning that if the UI framework changed, no core app logic would have to be rewritten.

### Model-View-Presenter
In the model-view-present (MVP) concept, the view's responsibility is purely rendering the data and passing events back to the presenter. The presenter receives events from the view and triggers the appropriate business logic, handing the results back off to the view for rendering. The presenter has no knowledge of the view's implementation, and both components interact with each other through interfaces. As with Clean Architecture, this helps ensure separation of responsibilities. If the view decides to change frameworks or other implementation details, the presenter itself does not need to be refactored.

### Editor Design
The basic concept of the editor is a hierarchy of input components capable of displaying data in editable fields. An editing context object is passed down the view hierarchy and contains the relevant variables, parameters, vehicle data, plugins, and imports needed for contextual rendering and other content. For example, initially the context has no parameters. However, when a function definition is rendered, the component uses the function data from the context to populate the parameters list. When this augmented context is passed down to the various command or function calls with the function definition, the autocomplete fields will be able to appropriately display the available function parameters.

### Drag and Drop
Drag and drop is achieved using `react-beautiful-dnd`, which relies on `Droppable`s and `Draggable`s. Logic in the editor determines whether a particular drag action (with start and end `Droppable`s) should be allowed, and what relevant lists should be updated. The lists are then updated and passed back to the presenter via `onChange` methods. Note that for the drag and drop to work, each `Draggable` must be uniquely identifiable. This means each command or function call needs to have a unique ID regardless of index in the list. In the current implementation, these unique IDs are added if missing and saved when the file is saved. However, if this is undesirable, the IDs could be removed before save since they are only critical for the drag and drop view functionality.

### Workspace File
Example
```json
{
    "pluginDir": "./backend/plugins/info/",
    "projectDir": "./backend/examples/aspect_project/scripts",
    "ccddAppsDir": "./backend/examples/aspect_project/ccdd_exports",
    "pythonScript": "./backend/main_application.py"
}
```

### Plugins
See `resources/plugins` for example plugin definitions.

### Vehicle Data
CCDD JSON app files.

## Codebase Tour
- `app/ui`: Contains UI and presentation level code
  - `editor`: Holds all the user interface components for the editor. The editor components are all treated as stateless with respect to the model data. That means that modifying a value in the editor component (at any level) does not immediately change the "truth" model object for the file being edited. Instead, the state data is copied, edited, and passed back up the hierarchy via an `onChange` method. This ensures that business logic is not handled in the components themselves, which only deal with rendering logic (i.e., filtering autocomplete options).
    - `components`: Library of smaller components used by the file editor component
    - `CtfFileEditor.tsx`: Main file for the editor. This file contains change handlers for many of its subcomponents and a few lengthy methods necessary for drag and drop via `react-beautiful-dnd`.
  - `home`: Contains the home view and presenter
    - `HomePresenter.ts`: The presenter in the Model-View-Presenter paradigm for the home screen. The present handles all interaction with the model and domain use cases, abstracting these operations from the rendering logic in the view itself.
    - `HomeView.tsx`: Renders the home view, including the file editor component, if a file is being edited.
  - `runstatus`: Contains the run status view and presenter
    - `RunStatusPresenter.ts`: The presenter for the run status modal. Handles the interaction with the domain use cases for running the tests, including creating the run status listener and the script runner itself.
    - `RunStatusView.tsx`: The view for the run status modal. Given a run status object, it renders the data as a tree. Also provides logic for showing notifications that might occur during the test run.
    - `StatusIcon.tsx`: A component for rendering a status icon for the run status. One convenient spot to change how statuses are rendered when a test is run.
  - `util`: Contains several view/Electron-related utilities to open files and folders
  - `index.tsx`: The "main" function for the view. The entrypoint for creating and rendering the root view component (`HomeView`).
  - `PaneHeader.tsx`: A styled pane header
  - `FilePane.tsx`: A file tree pane with support for a context menu. Context menu events are passed up via a callback. Supports context menu icons by accepting `ReactNode`s as part of the context menu definition object.
- `domain`: Contains business logic use cases
  - `builders`: Use cases for building default or empty model objects
  - `editor-actions`: Business logic related to editing test case files
  - `exporters`: Use cases to save the test case file
  - `file-util`: General utility logic for working with various file types
  - `loaders`: Use cases for loading data and opening/setting up a workspace
  - `run`:
    - `CtfScriptRunner.ts`: The code that calls the backend run script
    - `RunStatusListener.ts`: Creates a UDP server, parses the data as JSON, and passes back run status messages. Will need to be modified to support passing back input request messages as well.
  - `jsonclone.ts`: A utility for deep cloning an object via `JSON.stringify/JSON.parse`
- `electron`: Holds Electron startup script
- `model`: Model data objects
  - `ccdd-json.ts`: Typescript interfaces for CCDD JSON vehicle data definitions
  - `ctf-engine.ts`: Typescript interfaces for backend socket JSON messages
  - `ctf-file.ts`: Typescript interfaces for CTF test case JSON files
  - `ctf-plugin.ts`: Typescript interfaces for CTF GUI plugins that define available instructions
  - `editing-context.ts`: Typescript interfaces for defining an editing context that ensures the editor has access to vehicle data, plugins, functions, and other relevant information.
  - `tree.ts`: Typescript classes for a generic tree structure
  - `vehicle-data.ts`: Typescript classes for storing vehicle data processed from CCDD JSON files

## Build Tools
### Babel
Babel compiles bleeding-edge Javascript & Typescript code down into Javacript that runs in standard browsers.

### Electron
Electron allows us to take our web app and run it via Node and Chromium as a standalone desktop app.

### React
React gives us a nice, object-oriented way to build UI components for our app.

### Typescript
Strict type checking for Javascript. Helps "tighten" up Javascript's normally "loose" typing.

### Webpack
Webpack packages our source files and uses the Typescript and Babel compilers. It can generate regular or minified output depending on if we're in development or production mode.

## References
- electron-react-ts-starter (https://github.com/mbr4477/electron-react-ts-starter)

## Known Issues
- No support for range comparison operators
- When using hot reload, sometimes opening a workspace fails
- Backend only works on Linux due to `os` and `pwd` module calls
- The `config.ini` file must be in the same directory as `main_application.py`. When the UI runs the backend script, it uses `main_application.py`'s directory as the working directory to ensure the script can find the `config.ini` file.

## Contact
Matthew Russell<br/>
Graduate Ph.D. Pathways Intern, ER6<br/>
NASA Email: matthew.russell@nasa.gov<br/>
School Email: matthew.russell@uky.edu

