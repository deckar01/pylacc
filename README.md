# PyLACC

Python Linear Analog Circuit Caclulator

## API

`from pylacc.circuit import *`

### Components

- Voltage Source:
    - `e(voltage, frequency, **)`
- Current Source:
    - `i(amperage, frequency, **)`
- Resistor:
    - `r(resistance, frequency, **)`
- Capacitor:
    - `c(capacitance, **)`
    - `xc(reactance, **)`
- Inductor:
    - `l(inductance, **)`
    - `xl(reactance, **)`
- `**`
    - `E` Voltage (complex, phasor)
    - `I` Current (complex, phasor)
    - `Z` Impedence (complex, phasor) (alias `R`)
    - `C` Capacitance (positive, real)
    - `L` Inductance (positive, real)
    - `XC` Capacitive Reactance (positive, real)
    - `XL` Inductive Reactance (positive, real)
    - `F` Frequency (positive, real)
    - `PT` True Power (positive, real) (alias `P`)
    - `PR` Reactive Power (positive, real)
    - `PA` Apparent Power (positive, real)

#### Complex Arguments

`1.0 + 1.0j` (complex)

#### Phasor Arguments

`(radius, angle)` (tuple)

## Units

- `k` 10^3
- `M` 10^6
- `G` 10^9
- `T` 10^12
- `m` 10^-3
- `u` 10^-6
- `n` 10^-9
- `p` 10^-12

## Series Circuits `+`

`e(12) + r(100) + r(300)`

```
+(12V 30mA)
+-S[12V](30mA 360mW)
+-R[100Ω](3V 30mA)
+-R[300Ω](9V 30mA)
```

## Parallel Circuits `/`

`e(12, 60) + xl(100) / xc(200) / r(300)`

```
+(12V 72.1∠-56.3°mA)
+-S[12V 60Hz](72.1∠-56.3°mA 865mVA)
+-/(12V 72.1∠-56.3°mA)
+ /-L[100Ω](12V 120∠-90°mA 265mH)
+ /-C[200Ω](12V 60∠90°mA 13.3μF)
+ /-R[300Ω](12V 40mA)
```

## Groups

Components can be grouped to prevent further concatenation.

```
FILTER = (l(1e-3) + c(0.0022e-6)).g
C = e(10, 107e3) + FILTER + r(100)
C.solve()
FILTER
```

```
+(380∠-87.8°mV 99.9∠2.18°mA)
+-L[1mH](67.2∠92.2°V 99.9∠2.18°mA 672Ω)
+-C[2.2nF](67.6∠-87.8°V 99.9∠2.18°mA 676Ω)
```

## TODO

- Support multiple sources
