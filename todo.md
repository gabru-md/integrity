## Todos

Todos are listed by Apps and Libs. Apps are for work on functionality. Libs are framework level changes.

### Apps

* [X] ~~Need an app for notifications -> need to enable queue processor first~~
* [ ] enforce temporal conditions on contracts
* [ ] what exactly is frequency and how to use it properly needs to be documented
* [ ] tailscale for making it accessible to world
* [X] ~~should all contracts be linked to a trigger event~~ - No, there can be unlinked contracts. I need to refine what
  sentinel should do.
* [X] ~~finish sentinel condition validation~~
* [X] ~~Make a dashboard of widgets from different apps~~
* [x] enable notifications from emails on iphone
* [x] make an easy shortcut creator which can be imported on iphone and iwatch easily instead ot
  f shortcuts app
* [x] the shortcuts need to change. With shortcut I can define a specific shortcut and it will be invoked by a get call
  to the shortcut id instead of actual call
* [ ] cleanup todos
* [ ] cleanup comments from the code added by ai
* [ ] setup cameras
* [ ] setup beacons
* [ ] code for indoor positioning system
* [ ] Add logs or some visualizer for processes on ui

### Libs
* [ ] get rid of _process_model_data func this can be done in the service
* [ ] Add c_util.py and a_util.py for collections and array utils
* [X] ~~Add process runner~~
* [X] ~~Make an app wrapper~~
* [X] ~~Create a queue database with queuestats table for enabling queue processor~~
* [X] ~~Add queue db related info to .env~~
* [X] ~~Add docs about qprocessor.py~~
* [ ] Add readme for .env variables
* [ ] add dependency injection to manage many db objects

### Database

* [x] Cleanup the queuestats table of unexpected sentinels
* [ ] Cleanup the testing events from events database
