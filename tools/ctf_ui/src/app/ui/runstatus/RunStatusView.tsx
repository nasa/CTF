/*
# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# Copyright (c) 2019-2022 United States Government as represented by the
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

import { Empty, Result, Tree, Button, Card, message, Timeline, Typography, Divider, Checkbox, Row, Collapse, Col } from 'antd';
import * as React from 'react';
import { CtfEngineRunStatusMsg , CtfInstructionStatus, CtfEngineScriptStatus} from '../../../model/ctf-engine';
import { CtfFile } from '../../../model/ctf-file';
import {
    IRunStatusPresenter,
    IRunStatusView,
    RunStatusPresenter
} from './RunStatusPresenter';
import { StatusIcon } from './StatusIcon';
import Text from 'antd/lib/typography/Text';

import Paragraph from 'antd/lib/typography/Paragraph';
import TimelineItem from 'antd/lib/timeline/TimelineItem';
import { cpus } from 'os';
import Title from 'antd/lib/skeleton/Title';

import { animateScroll } from "react-scroll";

const OutputStyle: React.CSSProperties = {
    maxHeight: '275px',
    overflow:'scroll'
};

const TreeNode = Tree.TreeNode;
const  {Panel}   = Collapse;

export interface RunStatusProps {
    scripts: string[];
    pythonCommand: string;
    projectDir: string;
    onComplete: () => void;
}

export interface RunStatusState extends RunStatusProps {
    presenter: IRunStatusPresenter;
    runStatus?: CtfEngineRunStatusMsg;
    error?: {
        title: string;
        message: string;
    };
    output?: string;
    complete: boolean;
    debug_output: boolean;
}

function FindTreeKeys ( scripts: CtfEngineScriptStatus[] ) {

    let keys = [];

    for (let script of scripts) {

        keys.push(script.path)

        for (let test of script.tests) {
            keys.push(test.test_number)
        }
    }

    return keys;

}


let args_index: number = 1;


function PayloadParameters ( data ) {

    args_index++;

    if ( data instanceof Array && data.length > 0) {

        return (
            <TreeNode selectable={false}
                 title={
                    <span>
                          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                        <Button type="dashed" size="small"  disabled style = {{width: 180}}>  { data[0] }  </Button>
                        <Text type="secondary" style = {{ marginLeft: 30 }}>  { data[1] }  </Text>

                     </span>
                }

                key={ data[0] +  data[1]+ args_index.toString()}
            >

             </TreeNode>
        )

    }


}

function ArgsParameters ( data ) {


    let tempstr:string = JSON.stringify(data);

    tempstr = tempstr.substr(1,(tempstr.length-2) )

    const keys = Object.keys(data);

    let variable = null;
    let compare = null;
    let value   = null;


    // handle a special case
    if ( (typeof(data) == "object")  && ('variable' in data) ) {
        variable = data["variable"];
    }

    if ( (typeof(data) == "object")  && ('compare' in data) )  {
        compare = data["compare"];

    }

    if ( (typeof(data) == "object")  && ('value' in data) )  {
           value = data['value'][0];
    }

    //console.log("ArgsParameters =", tempstr);

    // handle a general case
    const argsarray = Object.entries(data);


    let argskey   = null;
    let argsvalue = null;
    let argsvaluearray = [];

    if (variable == null) {
        argskey   = argsarray[0][0];
        argsvalue = argsarray[0][1];
        //console.log("     ArgsParameters argsvalue =", argsvalue);

        if ( (typeof(argsvalue) == "object") && !(argsvalue instanceof Array)  ) {

            const argskeys = Object.keys(argsvalue);
            argskeys.forEach( function(key ) {
                argsvaluearray.push( { [key]: argsvalue[key] } );
             } );
        }
    }


    args_index++;

    if (variable != null) {

        return (
            <TreeNode selectable={false}
                 title={
                    <span>
                          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                        <Button type="dashed" size="small"  disabled style = {{width: 220}}>  { variable }  </Button>
                        <Button type="text"   size="small"  disabled style = {{width: 120}}>  { compare }   </Button>
                        <Button type="text"   size="small"  disabled style = {{width: 120}}>  { value }     </Button>

                     </span>
                }

                key={tempstr + args_index.toString()}
            >

             </TreeNode>
        )

    } else if  (argsvaluearray.length == 0)  { // the value is numbers or strings
        return (
            <TreeNode selectable={false}
                 title={
                    <span>
                          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                        <Button type="dashed" size="small"  disabled style = {{width: 220}}>  { argskey }  </Button>
                        <Text type="secondary" style = {{ marginLeft: 30 }}>  {argsvalue}  </Text>
                     </span>
                }

                key={tempstr + args_index.toString()}
            >

             </TreeNode>
        )

    } else { // the value is json object , recursion call itself
        return (
            <TreeNode selectable={false}
                 title={
                    <span>
                          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                        <Button size="small"  disabled style = {{width: 220}}>  { argskey }  </Button>
                     </span>
                }

                key={tempstr + args_index.toString()}
            >
             { argsvaluearray.map(ArgsParameters)}
             </TreeNode>
        )

    }



}

function CommandData ( data ) {

    // most data obj has only one single key - value
    // most args are array of obj, few are obj of obj
    const textstyle = {
        marginLeft: 20,
        display: "none"
    };


    let tempstr:string = JSON.stringify(data);

    tempstr = tempstr.substr(1,(tempstr.length-2) )

    const keys = Object.keys(data);

    let key = keys[0];
    let value = data[key];
    let argsarray = [];

   // console.log("CommandData =", tempstr);

    if ( value instanceof Array ) {
        argsarray = value;
        value = " " ;
    } else  if (typeof(value) == "object" ) {

        const argskeys = Object.keys(value);
        argskeys.forEach( function(key ) {
           argsarray.push( { [key]: value[key] } );
         } );

        if (argskeys[0] == 'Payload') {

            if ( (typeof(argsarray[0]) == "object") && !(argsarray[0] instanceof Array ) ) {

                if ( 'Payload' in argsarray[0]) {
                    key = "Payload";
                }
            }
        }

        value = " " ;

    }

    args_index++;

    if (key == "Payload") {
        //convert Payload object' value to an array
        let payloadvalue =  argsarray[0]['Payload'];
       // payloadvaluearray is array of array
        const payloadvaluearray = Object.entries(payloadvalue);

        return (
        <TreeNode selectable={false}
             title={
                <span>

                      &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                       <Button size="small" style = {{width: 120}}>  { key }  </Button>
                       <Text type="secondary" style = {{ marginLeft: 30 }}>  {value}  </Text>

                </span>
            }

             key={tempstr + args_index.toString()}
         >

        { payloadvaluearray.map(PayloadParameters)}

        </TreeNode>

        )

    }

    return (
        <TreeNode selectable={false}
             title={
                <span>

                      &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                       <Button size="small" style = {{width: 120}}>  { key }  </Button>
                      <Text type="secondary" style = {{ marginLeft: 30 }}>  {value}  </Text>

                </span>
            }

             key={tempstr + args_index.toString()}
         >

        { argsarray.map(ArgsParameters)}

        </TreeNode>
    )

}

function Command ( cmd:CtfInstructionStatus, i:number ) {

    args_index += 1;

    let data = cmd.data;

    let dataproparry:Array<object>  = [];
    const keys = Object.keys(data);
    keys.forEach(function(key){
        dataproparry.push( { [key]: data[key] } );
    });


    return (
        <TreeNode
            selectable={false}
            title={
                <span>
                    <Button size="small">  {cmd.instruction}  </Button>
                    <Text type="secondary" style={{ marginLeft: 10 }}>  {cmd.details}  </Text>
                    <Text type="secondary" style={{ marginLeft: 10 }}>  {cmd.comment}  </Text>
                </span>
            }
            icon={ <StatusIcon  status={cmd.status }  />  }
            key={cmd.instruction+(i+args_index+100).toString()}

        >
         { dataproparry.map(CommandData)}


        </TreeNode>

    );
}

export class RunStatusView
    extends React.Component<RunStatusProps, RunStatusState>
    implements IRunStatusView {
    constructor(props: RunStatusProps) {
        super(props);
        this.linenumber = 0;
        this.ctf_output_array = []

        this.state = Object.assign(
            {
                presenter: new RunStatusPresenter(
                    this,
                    props.pythonCommand,
                    props.projectDir,
                    props.scripts
                ),
                output: "",
                complete: false,
                debug_output: false
            },
            props
        );
    }

    runDidFinish = (): void => {
        this.state.onComplete();
        this.setState({ complete: true });
        this.ctf_output_array = []
    };

    showMessage = (content: string): void => {
        message.info(content);
    }

    showError = (title: string, message: string): void => {
        this.state.onComplete();
        this.setState({ error: { title, message } });
    };

    showOutput = async (content: string) => {
        await this.setState(prevState => ({
            output: content
        }) );
        this.updateCTFOutput()
    }

    scrollToBottom() {
        animateScroll.scrollToBottom({
          containerId: "output_log"
        });
    }

    updateCTFOutput() {
        const MAX_LINES = 300;
        let output_temp = []
        let content_array = this.state.output.split("\n");
        let content_lines = content_array.length;
        let output_lines = this.ctf_output_array.length;

        // do not need to keep all ctf output, remove some lines
        if ( (content_lines + output_lines) >= MAX_LINES ) {
            if (content_lines >= MAX_LINES) {
                this.ctf_output_array = []
                this.ctf_output_array.push( {line_color: 'blue', key : ++this.linenumber, line: "  ..."})
            } else {
                let delete_lines = output_lines - (MAX_LINES - content_lines) ;
                this.ctf_output_array.splice(0, delete_lines, {line_color: 'blue', key : ++this.linenumber, line: "  ..."} )
            }
        }

        // add the new lines to ctf_output_array
        content_array.map((content) => {
          let color = 'blue'
          let label = "INFO"
          if (content.indexOf("FAIL") > 0){
             color = 'red';
             label = "FAIL";
          }
          else if (content.indexOf("PASS") > 0){
             color = 'green';
             label = "PASS";
          }

          let cur_line = { line_color: color, key : ++this.linenumber, line: content}

          if (content.length > 2) { this.ctf_output_array.push(cur_line); }
        });
    };

    componentDidMount = () => {
        this.state.presenter.viewDidLoad();
    };



    componentWillUnmount = () => {
        this.state.presenter.viewWillUnload();
    };

    showRunStatusMsg = (msg: CtfEngineRunStatusMsg) => {
        this.setState({ runStatus: msg });
    };

    componentWillReceiveProps(props: RunStatusProps) {
        this.setState(props);
    }

    render() {
        if (this.state.runStatus) {
            this.scrollToBottom();
            const outputStyle = {
              whiteSpace: "pre-line",
              overflowY: "scroll",
              maxHeight: "12em"
            }

           // console.log("TW DEBUG:: ", this.state.runStatus.scripts[0].tests);
            let expandkeys = FindTreeKeys(this.state.runStatus.scripts);
            args_index = 1;

            return (
                <div>
                     <Tree defaultExpandedKeys={expandkeys} showIcon>
                        {this.state.runStatus.scripts.map(script => (
                            <TreeNode
                                title={script.test_script_number}
                                icon={<StatusIcon status={script.status} />}
                                key={script.path}
                            >
                                {script.tests.map(test => (
                                    <TreeNode
                                        title={test.test_number}
                                        icon={<StatusIcon status={test.status} />}
                                        key={test.test_number}
                                    >
                                   { test.instructions.map(Command)}


                                    </TreeNode>

                                ))}

                            </TreeNode>
                        ))}
                    </Tree>

                    <Divider type="horizontal" />
                    <Row>
                    <Col span={8}>
                        <Typography.Title level={4}>CTF Output</Typography.Title>
                    </Col>
                    <Col span={8} offset={8}>
                    <Checkbox onChange={(e) => {
                        this.setState({"debug_output": e.target.checked});
                        }
                    }>
                            Debug Output
                    </Checkbox>
                    </Col>
                    </Row>
                    <div id="output_log" style={OutputStyle}>
                    <Timeline pending={!this.state.error && !this.state.complete}>
                      {this.ctf_output_array.map((value) => {
                        return (
                           <Timeline.Item color={value.line_color} key = {value.key}>
                                <Typography.Text code={true}>{value.line.replace(/].*\*\*\*/, '').substr(1)}</Typography.Text>
                            </Timeline.Item>
                        )
                    })}

                    </Timeline>
                    </div>
                    </div>
            );
        } else if (this.state.error) {
            return (
                <Result
                    status="error"
                    title={this.state.error.title}
                    subTitle={this.state.error.message}
                />
            );
        } else {
            return <Empty description="No Run Status" />;
        }
    }
}
