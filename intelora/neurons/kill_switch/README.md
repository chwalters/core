# kill_switch

## Synopsis

This neuron exits the Intelora process.

## Installation

CORE NEURON : No installation needed.  

## Options

No parameters

## Return Values

No returned values

## Synapses example

Simple example : 

```yml
  - name: "stop-intelora"
    signals:
      - order: "goodbye"
    neurons:
      - kill_switch    
```


## Notes

