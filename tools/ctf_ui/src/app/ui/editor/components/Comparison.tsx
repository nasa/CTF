/*
# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2024 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration. All Rights Reserved.
#
# This software is governed by the NASA Open Source Agreement (NOSA) License and may be used,
# distributed and modified only pursuant to the terms of that agreement.
# See the License for the specific language governing permissions and limitations under the
# License at https://software.nasa.gov/ .
#
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either expressed or implied.
*/

import { Input, Select, Button, Tag, Checkbox} from "antd";
import { CascaderOptionType, CascaderExpandTrigger } from "antd/lib/cascader";
import * as React from "react";
import {useRef, useEffect, useState} from "react";
import { CtfComparisonType } from "../../../../model/ctf-file";
import { EditingContext } from "../../../../model/editing-context";
import { VehicleData } from "../../../../model/vehicle-data";
import { AutoCompleteField } from "./AutoCompleteField";
import { stringify } from "querystring";

const { Option } = Select;

const mapVehicleDataToTelemetryFields = (
    vehicleData: VehicleData,
    midFilter?: string
): string[] => {
    return vehicleData.telemetry
        .filter(t => midFilter && t.mid === midFilter && midFilter.length > 0)
        .map(t => t.params.filter(p => p !== undefined).map(p => p.name))
        .flat();
};

const mapVehicleDataToTelemetryFieldsType = (
    vehicleData: VehicleData,
    midFilter?: string
): string[] => {
    return vehicleData.telemetry
        .filter(t => midFilter && t.mid === midFilter && midFilter.length > 0)
        .map(t => t.params.filter(p => p !== undefined)).flat()
        .reduce( (acc, cur) => { acc[cur.name] = cur.data_type ;  return acc; }, {} );

};

const mapVehicleDataToTelemetryFieldEnums = (
    vehicleData: VehicleData,
    midFilter: string
): string[] => {
    return vehicleData.telemetry.filter(t => t.mid == midFilter)
        .map(t => t.params.filter(p => p !== undefined).map(p => p.name).flat())
        .flat();
};

function setValue(object, path, value): void {
    // console.log(object)
    // console.log(path)
    // console.log(value)
    var keys = path.split('.'),
        last = keys.pop();
    keys.reduce(function (o, k) { return o[k] = o[k] || {}; }, object)[last] = value;
}


const mapObjectsToCascaderOptions = (obj) => {
    // console.log(obj)
    var options: CascaderOptionType[] = [];
    const iterate = (obj: CascaderOptionType, prefix): CascaderOptionType[] => {
        if (prefix.length > 0){
            prefix = prefix + '.'
        }
        var new_options: CascaderOptionType[] = [];
        Object.getOwnPropertyNames(obj).forEach(key => {
            if (obj[key] instanceof Object) {
                var option: CascaderOptionType = {label: key, value: prefix + key, children: iterate(obj[key], prefix + key)}
                // console.log(option)
                new_options.push(option)
            }
            else{
                // console.log("Primitive Option of type " + typeof(obj[key]))
                // console.log(obj[key])
                var option: CascaderOptionType = {label: key, value: prefix + key}
                // console.log(option)
                new_options.push(option)
            }
        })
            return new_options
    }

    Object.getOwnPropertyNames(obj).forEach(key => {
        // console.log("Iterating on " + key)
        if (obj[key] instanceof Object) {
            var new_options = iterate(obj[key], key)
            options.push({label: key, value: key, children: new_options});
        }
        else{
            options.push({label: key, value: key});
        }
    })

    return options
}

// function mapObjectsToCascaderOptions (obj, prev_value, options) {
//     for (var k in obj) {
//       if (typeof obj[k] === 'object' && obj[k] !== null) {
//         var option: CascaderOptionType[] = {label: k, value: prev_value + '.' + k}
//         var children = mapObjectsToCascaderOptions(obj[k], k, option)
//         if (children)
//             option.children = children;
//         options.push(option)
//       }
//       else if (obj.hasOwnProperty(k)) {
//         options.push({label: k, value: prev_value + '.' + obj[k]})
//         return options
//       }
//     }
//     console.log(options)
//   }

const mapDotNotationToCascaderOptions = (
    values: string[]
): CascaderOptionType[] => {
    var options_dict : Object = {};
    values.forEach(value =>{
        var pieces = value.split(".");
        setValue(options_dict, value, pieces[pieces.length - 1])
    })
    var options: CascaderOptionType[] = mapObjectsToCascaderOptions(options_dict)
    // console.log(options)
    return options
};


export const Comparison = ({
    className,
    style,
    comparison,
    context,
    tlmMid,
    onChange
}: {
    className?: string;
    style?: object;
    comparison: CtfComparisonType;
    context: EditingContext;
    tlmMid?: string;
    onChange?: (next: CtfComparisonType) => void;
}) => {
    const changeHandler = (update: object, rm_tolerance: boolean) => {
        let newCompare = Object.assign({}, comparison, update);
        if (rm_tolerance === true) {
            let { tolerance,tolerance_plus,tolerance_minus, ...newCompare_2} = newCompare;
            newCompare = newCompare_2;
        }
        if (onChange) onChange(newCompare);
    };

    const tlm_fields_types = mapVehicleDataToTelemetryFieldsType(context.vehicleData, tlmMid);

    const comp_var = comparison.variable ?  comparison.variable : 'undefined';
    const comp_var_type = tlm_fields_types[comp_var];

    const dataSource = [
        {
            label: "Telemetry",
            value: "Telemetry",
            children: mapDotNotationToCascaderOptions(
                mapVehicleDataToTelemetryFields(context.vehicleData, tlmMid)
            )
        },
        // {
        //     label: "Enumerations",
        //     value: "Enumerations",
        //     children: mapVehicleDataToTelemetryFieldEnums(
        //         context.vehicleData,
        //         tlmMid
        //     ).map(e => ({ label: e, value: e }))
        // },
        {
            label: "Parameters",
            value: "Parameters",
            children: context.parameters.map(v => ({ label: v, value: v }))
        },
        {
            label: "Variables",
            value: "Variables",
            children: context.variables.map(v => ({ label: v, value: v }))
        }
    ];
    if (tlmMid && tlmMid.length === 0) tlmMid = undefined;

    let float_compare = false;
    if ( comparison.compare.includes("==") || comparison.compare.includes("!=") )
          float_compare = true;


    return (
        <div className={className} style={style}>
            <Input.Group compact>
                <AutoCompleteField
                    dataSource={dataSource}
                    placeholder=""
                    defaultValue={comparison.variable}
                    onChange={value => {
                        let rm_tolerance = false;
                        if (  ! (comp_var_type == undefined || comp_var_type == 'double' || comp_var_type == 'float') ) {
                            rm_tolerance = true;
                        }
                        changeHandler({ variable: value }, rm_tolerance);
                      }
                    }
                />
                <Select
                    size="small"
                    defaultValue={[comparison.compare]}
                    onChange={  value => {
                        let rm_tolerance = false;
                        if ( !(value === '==' || value === '!=') ) {
                            rm_tolerance = true;
                        }
                        changeHandler({ compare: value }, rm_tolerance);
                      }
                    }
                    style={{ width: 100 }}
                >
                    <Option key="==">==</Option>
                    <Option key="!=">!=</Option>
                    <Option key=">">&gt;</Option>
                    <Option key="<">&lt;</Option>
                    <Option key=">=">&gt;=</Option>
                    <Option key="<=">&lt;=</Option>
                    <Option key="streq">streq</Option>
                    <Option key="strneq">strneq</Option>
                    <Option key="regex">regex</Option>
                </Select>
                <Input
                   style={{ width: 120, height: 24 }}
                   defaultValue={comparison.value !== undefined ? comparison.value: ""}
                   autoFocus={false}
                   onBlur={ e => {
                     let num_converted = Number(e.target.value)
                     let update = {value : num_converted}

                     if ( comparison.compare.includes("str") ) update.value = e.target.value

                     changeHandler(update)
                   }}
               />

               { ( float_compare == true && (comp_var_type == undefined || comp_var_type == 'double' || comp_var_type == 'float') ) &&
                 <>
                    <Tag style={{ width: 120, height: 24, fontSize: 15 }} >  tolerance_minus  </Tag>

                    <Input
                       style={{ width: 80, height: 24 }}
                       defaultValue={comparison.tolerance_minus !== undefined ? comparison.tolerance_minus: ""}
                       autoFocus={false}
                       onBlur={ e => {
                         let num_converted = Number(e.target.value)
                         let update = {tolerance_minus : num_converted}
                         if (isNaN(num_converted)) update.tolerance_minus = e.target.value
                         // could not use { value: (+e.target.value? +e.target.value: e.target.value) }
                         // if the input is "0", convert to 0, but 0? is false, so value is set to "0" instead of 0 (number)
                         changeHandler(update);
                       }}
                   />

                    <Tag style={{ width: 120, height: 24 , fontSize: 15}} >  tolerance_plus  </Tag>

                    <Input
                       style={{ width: 80, height: 24 }}
                       defaultValue={comparison.tolerance_plus !== undefined ? comparison.tolerance_plus: ""}
                       autoFocus={false}
                       onBlur={ e => {
                         let num_converted = Number(e.target.value)
                         let update = {tolerance_plus : num_converted}
                         if (isNaN(num_converted)) update.tolerance_plus = e.target.value
                         changeHandler(update)
                       }}
                    />

                 </>
               }

            </Input.Group>
        </div>
    );
};

export const Condition = ({
    className,
    style,
    comparison,
    context,
    tlmMid,
    onChange
}: {
    className?: string;
    style?: object;
    comparison: CtfComparisonType;
    context: EditingContext;
    onChange?: (next: CtfComparisonType) => void;
}) => {
    const changeHandler = (update: object ) => {
        const newCompare = Object.assign({}, comparison, update);
        if (onChange) onChange(newCompare);
    };

    return (
        <div style={style}>
            <Input.Group compact>
                <Input
                    style={{ width: 80, height: 24 }}
                    defaultValue={comparison.variable}
                    autoFocus={false}
                    onBlur={ e => changeHandler({ variable: e.target.value }) }
                />
                  <Select
                    size="small"
                    defaultValue={[comparison.compare]}
                    onChange={value => changeHandler( { compare: value }, 1)}
                    style={{ width: 100 }}
                >
                    <Option key="==">==</Option>
                    <Option key="!=">!=</Option>
                    <Option key=">">&gt;</Option>
                    <Option key="<">&lt;</Option>
                    <Option key=">=">&gt;=</Option>
                    <Option key="<=">&lt;=</Option>
                </Select>

                 <Input
                    style={{ width: 80, height: 24 }}
                    defaultValue={comparison.value}
                    autoFocus={false}
                    onBlur={ e => {
                      let num_converted = Number(e.target.value)
                      let update = {value : num_converted}
                      if (isNaN(num_converted)) update.value = e.target.value

                      // could not use { value: (+e.target.value? +e.target.value: e.target.value) }
                      // if the input is "0", convert to 0, but 0? is false, so value is set to "0" instead of 0 (number)
                      changeHandler(update)
                    }}
                />

            </Input.Group>
        </div>
    );
};


export const Event = ( {
    className,
    style,
    event,
    context,
    tlmMid,
    onChange
}: {
    className?: string;
    style?: object;
    event: CtfComparisonType;
    context: EditingContext;
    onChange?: (next: CtfComparisonType) => void;
}) => {
    const changeHandler = (update: object ) => {
        const newCompare = Object.assign({}, event, update);
        if (onChange) onChange(newCompare);
    };


    return (
        <div style={style}>
            <Input.Group compact>
                <Tag style={{ width: 85, height: 24 }} >  app_name  </Tag>
                <Input
                    style={{ width: 60, height: 24 }}
                    defaultValue={event.app_name}
                    autoFocus={false}

                    onBlur={ e => {
                      let update = {app_name: e.target.value};
                      if ( !event.hasOwnProperty('event_str_args') )  update['event_str_args'] = '';
                      if ( !event.hasOwnProperty('is_regex') )  update['is_regex'] = false;
                      changeHandler(update)
                    }}
                />

                <Tag style={{ width: 70, height: 24 }} >  event_id  </Tag>
                <Input
                    style={{ width: 60, height: 24 }}
                    defaultValue={event.event_id}
                    autoFocus={false}
                    onBlur={ e => {
                      let num_converted = Number(e.target.value)
                      let update = {event_id : num_converted}
                      if (isNaN(num_converted)) update.value = e.target.value
                      // could not use { value: (+e.target.value? +e.target.value: e.target.value) }
                      // if the input is "0", convert to 0, but 0? is false, so value is set to "0" instead of 0 (number)
                      changeHandler(update)
                    }}
                 />

                 <Tag style={{ width: 100, height: 24 }} >  event_str_args  </Tag>
                 <Input
                     style={{ width: 60, height: 24 }}
                     defaultValue={event.event_str_args}
                     autoFocus={false}
                     onBlur={ e => changeHandler({ event_str_args: e.target.value }) }
                 />

                 <Tag style={{ width: 70, height: 24 }} >  is_regex  </Tag>
                 <Checkbox style={{ width: 40, height: 24, paddingLeft: 10, paddingTop:2 }}
                     className={"ant-input"}
                     defaultChecked = {event.is_regex? true: false}
                     checked = {event.is_regex? true: false}
                     onChange={e => {
                         let new_value = e.target.checked;
                         let update = {is_regex : new_value};
                         changeHandler(update);
                     }}
                 >
                 </Checkbox>

                  <br />

                 <Tag style={{ width: 70, height: 24 }} >  event_str  </Tag>
                 <Input
                     style={{ width: 470, height: 24 }}
                     defaultValue={event.event_str}
                     autoFocus={false}
                     onBlur={ e => changeHandler({ event_str: e.target.value }) }
                 />

            </Input.Group>
        </div>
    );
};
