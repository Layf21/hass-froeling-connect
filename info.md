# Home Assistant - Froeling Connect integration

This is a custom component to allow you to manage and control your Fröling devices in Home Assistant using the unofficial API.  
This component is currently in beta. It works, but it may be unstable.

### Setup

Use the frontend to initialize the component. Please enter your E-Mail address, password and preferred language code (en, de, ...).

### Features

* Automatically discovers your facilities and components
* Monitor and set parameters 
* Groups entities into devices
* Compatible with all Fröling components (in theory)
* Uses persistent token and only reauthenticates when necessary
* Configuration via UI
* Completely async

### Issues

I am aware of these issues/missing features, and I am planning to fix/implement them soon.  

* This is an unofficial implementation of the API. Updates from Fröling may break this component.
* I can't test this component for every possible Fröling setup. There may be errors I have not anticipated.
* Maybe there is an API rate limit I am not aware of. Waits 0.5s between API calls.
* Not all parameters are implemented. Known missing:
   - Dates
   - Ignition
   - "Heating circuit operating mode can be edited"  
  
  Skipped parameters are logged in debug mode. Open an issue to report any further missing parameters.

### TODO:

Most of these do not impact the functionality of the integration.

- [ ] Centralize the platform-distribution (what platform for what parameter)
- [ ] Give every entity device class (manual map)
- [ ] Handle internet unavailable
- [ ] Disable less popular entities by default
- [ ] Use `available` property
- [ ] Optimize API calls: don't fetch disabled components
- [ ] Implement Code Tests
- [ ] Clean entity and device registry when parameters disappear/change
- [ ] Comment/Type and clean code

> ### DISCLAIMER:
> I am not responsible for any damage that may arise from using this software.  
> Use at your own risk.
