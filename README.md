[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

# Home Assistant - Froeling Connect integration

This is a custom component to allow you to manage and controll your Fröling devices in Home Assistant using the unofficial API.  
This component is currently in beta. It works for me, but it may be unstable. It might take some time for me to get around to implementing fixes as I am rather busy right now.

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


## GEN_NXG (read-only)

GEN_NXG installations use a separate `/nxg/facility/.../web` API and nested
`valueItems` in `topView`, `listView`, and `additionalView`. This integration
supports the observed `Boiler`, `HeatingCircuit`, and `BufferTankSystemDual`
component types. Other NXG components are deliberately skipped for now.

The adapter reuses the existing authenticated Fröling Connect session. It exposes
numeric values, boolean states and enumerated values as sensors. All NXG values
remain read-only, including values marked editable in the portal, regardless of
the integration's send-changes setting. Free text, timestamps and schedules are
not exposed. Unknown component schemas are not claimed to be supported.

NXG polling uses a 120-second interval and a 60-second update timeout; the
existing interval and timeout for installations without NXG are unchanged.
With mixed generations in one entry, the shared coordinator uses NXG timing.

Manually validated on an S5 Dual 34 (GEN_NXG): 22 boiler entities, 11 dual-buffer
entities and 18 heating-circuit entities (51 in total), with values updating
across polling cycles. Counts vary with equipment and configuration. This does
not establish compatibility with all NXG boilers.

The unit tests use synthetic API fixtures; they contain no account identifiers,
serial numbers, addresses, credentials, or captured API UUIDs. Run them without
Home Assistant installed:

```sh
python3 -m venv .venv-tests
.venv-tests/bin/pip install froeling-connect==0.2.0
.venv-tests/bin/python -m unittest discover -s tests -v
```
