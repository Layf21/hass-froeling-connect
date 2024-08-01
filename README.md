[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

# Home Assistant - Froeling Connect integration

This is a custom component to allow you to manage and controll your Fröling devices in Home Assistant using the unofficial API.  
This component is currently in beta. It works, but it may be unstable.

### Features

* Automatically discovers your facilities and components
* Monitor and set parameters 
* Groups entities into devices
* Compatible with all Fröling components (in theory)
* Uses persistent token and only reauthenticates when necessary
* Configuration via UI
* Completely async

### Issues

I am aware of these issues/missing features and I am planning to fix/implement them soon.  

* This is an unofficial implementation of the api. Updates from Fröling may break this component.
* I can't test this component for every possible Fröling setup. There may be errors I have not anticipated.
* Maybe there is an api ratelimit I am not aware of. Waits 0.5s between api calls.
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
- [ ] Optimize api calls: don't fetch disabled components
- [ ] Implement Code Tests
- [ ] Clean entity and device registry when parameters disappear/change
- [ ] Comment/Type and clean code

> ### DISCLAIMER:
> I am not responsible for any damage that may arise from using this software.  
> Use at your own risk.

## Installation (HACS) - Highly Recommended

1. Have HACS installed, this will allow you to easily update
2. Add [https://github.com/Layf21/hass-froeling-connect](https://github.com/Layf21/hass-froeling-connect) as a custom
   repository as Type: Integration
3. Click install in the Integration tab
4. Restart HA
5. Navigate to _Integrations_ in the config interface.
6. Click _ADD INTEGRATION_
7. Search for _Fröling Connect_
   **NOTE:** If _Fröling Connect_ does not appear, hard refresh the browser (ctrl+F5) and search again
9. Enter your email, password & language when prompted.
10. Click _SUBMIT_
