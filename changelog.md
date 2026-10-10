## 4.3 (2026-10-10)
### Added
- decode the BM-2 appliance type datapoints (IDs 357/359/360/361) via the new
  type `DPT_HeatGenType`, so they read as "CHA" / "CGB-2" instead of a number
- `Ism8.decode_bitfield()` / `Ism8.is_bitfield()` resolve the BM-2 presence
  bitfields (IDs 251/355/356/358) into component names
- verified against an ISM8i FW1.90 with BM-2 that datapoint 251 is the one the
  module transmits for "Erkennung verfuegbare Heiz-/Mischerkreise"; the manual
  names 251 on p.22 and 351 on p.28, and 351 is never sent
### Fixed
- `decode_datapoint()` returns False again when a value is discarded; it had
  returned None since 4.2, which left test_jump_filter failing

## 4.2 (2026-10-10)
### Added
- added tests for DPT_VALUE_1_UCOUNT and DPT_VALUE_2_UCOUNT

## 4.1 (2026-10-08)
### Added
- added decoders for DPT_VALUE_1_UCOUNT and DPT_VALUE_2_UCOUNT.
### Fixed
- Fixed broken test for jump filter.

## 4.0 (2026-04-04)
### Fixed (Breaking Change!)
- fixed spelling error in "get_remote_ip_address"


## 3.5 (2026-03-20)
### Added
- change to case-instructions instead of if-else
- made encoding/decoding more concise with mapping of functions to datapoints
- added a callback on connection -> helpful in home assistant
- suppressed jumps to zero in temperature sensors (happens sometimes)
- implemented volume flow workaround for FW1.9

## 3.4 (2025-02-14)
### Added
- log level is inherited from calling module (Home Assistant)
- reduced several log level for errors to infos

## 3.3.2 (2025-01-14)
### Added
- Ignore datapoint if data length is zero
- Lib does not send ACK if data length is zero
- moved unit-tests to pytest framework
- added "known" undocumented datapoints 362,363,767
### Fixed
- refactored naming conventions / variable names
- improved network message handling and logging
- added missing docstrings
- fixed double entry in dictionary
- changed versioning to dynamic pyproject.toml
- trimmed down logging
- moved tests to test directory

## 3.3.1 (2024-12-27)
### Added
- new datapoints from FW1.90
- added new HVAC-Modes for/from CHA
- some refactoring, improved logging

## 3.2.4 (2024-07-02)
### Fixed
- fixed bug in time encoding, again

## 3.2.3 (2024-07-01)
### Fixed
- fixed bug in time encoding

## 3.2.2 (2024-06-21)
### Fixed
- fixed bug in date encoding

## 3.2.1 (2024-06-21)
### Fixed
- fixed some minor bugs, streamlined validation

## 3.2 (2024-06-14)
### New
- added reporting of version number
- added data integrity checks

### Fixed
- fixed errors in datapoint dictionary definition

## 3.1 (2024-06-08)
### New
- added support for TIME and DATE datapoints, read and write
- added callback-functionality to realize push-integration in home assistant
### Fixed
- one datapoint was missing. Fixed that.

## 3.0 (2024-01-18)
### New
- added/tested support for writing float datapoints to ISM8
- added undocumented datapoints instead of ignoring them
### Changes
- breaking change: renamed all devices to full name instead of abbreviation
- breaking change: deprecated function "read" replaced by "read_sensor"

## x.x.x
### New
- Everything
- started changelog at 3.0 (sorry)
