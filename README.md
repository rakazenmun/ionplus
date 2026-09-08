# IonPlus

Extension of tjcsl/ion.
(unofficial)

## Features

* **8th Period/Enrichment Auto Signup:** As soon as 8th period slots open, IonPlus will sign you up for it. If the activity is full, an email will be sent to you.
* **Auto Notifications:** Sends emails for bus updates, 8th period room information, and announcements.

## Repository Structure

* `solution.cpp`: Core application logic written for IonPlus.
* Supporting Files: Third-party boilerplate, external framework code, and system dependencies.

## Build & Setup

Compile `solution.cpp` using a C++17 compiler:

```bash
g++ -O2 solution.cpp -o ionplus
./ionplus