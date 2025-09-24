## Todos

Todos are listed by Apps and Libs. Apps are for work on functionality. Libs are framework level changes.

### Apps

* [ ] Need an app for notifications -> need to enable queue processor first
* [ ] enforce temporal conditions on contracts
* [ ] what exactly is frequency and how to use it properly needs to be documented
* [ ] tailscale for making it accessible to world
* [X] ~~should all contracts be linked to a trigger event~~ - No, there can be unlinked contracts. I need to refine what
  sentinel should do.
* [X] ~~finish sentinel condition validation~~
* [X] ~~Make a dashboard of widgets from different apps~~

### Libs

* [ ] Add c_util.py and a_util.py for collections and array utils
* [X] ~~Add process runner~~
* [X] ~~Make an app wrapper~~
* [X] ~~Create a queue database with queuestats table for enabling queue processor~~
* [X] ~~Add queue db related info to .env~~
* [X] ~~Add docs about qprocessor.py~~

### Database

* [ ] Cleanup the queuestats table of unexpected sentinels
* [ ] Cleanup the testing events from events database