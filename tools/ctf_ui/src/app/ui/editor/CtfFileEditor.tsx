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

import {
    Button,
    Collapse,
    Descriptions,
    Divider,
    Empty,
    Icon,
    Layout,
    PageHeader,
    Popconfirm,
    Row,
    Select,
    Tabs,
    Tag,
    Tooltip,
    Popover,
    Input,
    Checkbox,
    Form
} from 'antd';
import Text from 'antd/lib/typography/Text';
import * as React from 'react';
import ReactDOM from 'react-dom'
import { DragDropContext, DropResult } from 'react-beautiful-dnd';
import * as uuid from 'uuid/v4';
import { BuildEmptyCommand } from '../../../domain/builders/BuildEmptyCommand';
import { BuildEmptyFunctionCall } from '../../../domain/builders/BuildEmptyFunctionCall';
import { jsonclone } from '../../../domain/jsonclone';
import { CtfFile, CtfFunction, CtfTest } from '../../../model/ctf-file';
import { CtfPluginInstruction } from '../../../model/ctf-plugin';
import {
    EditingContext,
    EditingContextFunction
} from '../../../model/editing-context';
import {
    ButtonWithTopSpacing,
    DeleteButton
} from './components/ctf-file-editor-utils';
import { FunctionDefinition } from './components/FunctionDefinition';
import { LibraryGroup, LibraryPane } from './components/LibraryPane';
import { TestCase } from './components/TestCase';
import { AutoCompleteField } from './components/AutoCompleteField';
import { FormProps, FormComponentProps } from 'antd/lib/form';
import { RefObject } from 'react';
import { CheckCircleTwoTone , CloseCircleTwoTone, ShrinkOutlined } from '@ant-design/icons';


const { Panel } = Collapse;
const { Content, Sider } = Layout;

const PREFIX_SEPARATOR = '.';
const TEST_CASE_DROPPABLE_PREFIX = 'TEST_CASE' + PREFIX_SEPARATOR;
const FUNCTION_DEF_DROPPABLE_PREFIX = 'FUNCTION_DEF' + PREFIX_SEPARATOR;
const COMMAND_LIB_DROPPABLE_PREFIX = 'COMMAND_LIB' + PREFIX_SEPARATOR;
const FUNCTION_LIB_DROPPABLE_PREFIX = 'FUNCTION_LIB' + PREFIX_SEPARATOR;
const LOCAL_FUNCTION_GROUP_NAME = 'Local';

const substringAfter = (source: string, sep: string) => {
    return source.substr(source.indexOf(sep) + 1);
};

interface EditorProps extends FormComponentProps {
    ctfFile?: CtfFile;
    context?: EditingContext;
    showDirtyFlag: boolean;
    newRequirement?: string;
    newCoverage?: string;
    onChange?: (value: CtfFile) => void;
    onRenameFunction?: (oldName: string, newName: string) => void;
    onAddImportFile?: () => void;
    visible: boolean;
    functionData?: LibraryGroup[]
}

function hasErrors(fieldsError) {
    return Object.keys(fieldsError).some(field => fieldsError[field]);
  }

class CtfFileEditor extends React.Component<EditorProps, EditorProps, any> {
    constructor(props: EditorProps & FormComponentProps) {
        super(props);
        this.state = {
            ctfFile: props.ctfFile,
            context: props.context,
            showDirtyFlag: false,
            newRequirement: undefined,
            newCoverage: undefined,
            form: props.form,
            visible: false,
            functionData: []
        };
        this.reloadImports()
    }

    requirementsFormRef: RefObject<Form> = React.createRef();

    componentWillReceiveProps = (props: EditorProps) => {
        this.setState(props);
    };

    getList = (droppableId: string): Array<any> => {
        if (droppableId.startsWith(COMMAND_LIB_DROPPABLE_PREFIX)) {
            const group_name = substringAfter(droppableId, PREFIX_SEPARATOR);
            return this.state.context.plugins.find(
                p => p.group_name === group_name
            ).instructions;
        } else if (droppableId.startsWith(FUNCTION_LIB_DROPPABLE_PREFIX)) {
            const src = substringAfter(droppableId, PREFIX_SEPARATOR);
            return this.state.context.functions.filter(
                f =>
                    f.src === src ||
                    (f.src === undefined && src === LOCAL_FUNCTION_GROUP_NAME)
            );
        } else if (droppableId.startsWith(TEST_CASE_DROPPABLE_PREFIX)) {
            const caseNum = substringAfter(droppableId, PREFIX_SEPARATOR);
            return this.state.ctfFile.tests.find(t => t.test_number === caseNum)
                .instructions;
        } else if (droppableId.startsWith(FUNCTION_DEF_DROPPABLE_PREFIX)) {
            const functionName = substringAfter(droppableId, PREFIX_SEPARATOR);
            return this.state.ctfFile.functions[functionName].instructions;
        }
    };

    updateList = (droppableId: string, newValues: any[]) => {
        if (droppableId.startsWith(TEST_CASE_DROPPABLE_PREFIX)) {
            const caseNum = substringAfter(droppableId, PREFIX_SEPARATOR);
            const newCtfFile = jsonclone(this.state.ctfFile);
            newCtfFile.tests.find(
                t => t.test_number === caseNum
            ).instructions = newValues;
            if (this.state.onChange) this.state.onChange(newCtfFile);
        } else if (droppableId.startsWith(FUNCTION_DEF_DROPPABLE_PREFIX)) {
            const functionName = substringAfter(droppableId, PREFIX_SEPARATOR);
            const newCtfFile = jsonclone(this.state.ctfFile);
            newCtfFile.functions[functionName].instructions = newValues;
            if (this.state.onChange) this.state.onChange(newCtfFile);
        }
    };

    onDrop = (result: DropResult) => {
        if (!result.destination) return;
        if (result.destination.droppableId === result.source.droppableId) {
            // Dropped in same drop target
            const listCopy = Array.from(
                this.getList(result.destination.droppableId)
            );
            const [moving] = listCopy.splice(result.source.index, 1);
            listCopy.splice(result.destination.index, 0, moving);
            this.updateList(result.destination.droppableId, listCopy);
        } else if (
            result.source.droppableId.startsWith(
                COMMAND_LIB_DROPPABLE_PREFIX
            ) ||
            result.source.droppableId.startsWith(FUNCTION_LIB_DROPPABLE_PREFIX)
        ) {
            const element = result.source.droppableId.startsWith(
                COMMAND_LIB_DROPPABLE_PREFIX
            )
                ? BuildEmptyCommand.build(this.getList(
                      result.source.droppableId
                  )[result.source.index] as CtfPluginInstruction)
                : BuildEmptyFunctionCall.build(this.getList(
                      result.source.droppableId
                  )[result.source.index] as EditingContextFunction);
            const destListCopy = Array.from(
                this.getList(result.destination.droppableId)
            );
            // add to function as command
            destListCopy.splice(result.destination.index, 0, element);
            this.updateList(result.destination.droppableId, destListCopy);
        } else {
            return;
        }
    };

    onTestCaseChanged = (index: number, testCase: CtfTest) => {

        const newFile = jsonclone(this.state.ctfFile);
        newFile.tests[index] = testCase;
        this.setState({ ctfFile: newFile });
        if (this.state.onChange) this.state.onChange(newFile);
    };

    onFunctionDefChanged = (name: string, functionDef: CtfFunction) => {
        const newFile = jsonclone(this.state.ctfFile);
        newFile.functions[name] = functionDef;
        if (this.state.onChange) this.state.onChange(newFile);
    };

    onMetaDataChanged = (update: object) => {
        const newFile = Object.assign(jsonclone(this.state.ctfFile), update);
        if (this.state.onChange) this.state.onChange(newFile);
    };

    onDeleteTestCase = (index: number) => {
        const newFile = jsonclone(this.state.ctfFile);
        newFile.tests.splice(index, 1);
        if (this.state.onChange) this.state.onChange(newFile);
    };

    onDeleteFunction = (name: string) => {
        const newFile = jsonclone(this.state.ctfFile);
        delete newFile.functions[name];
        if (this.state.onChange) this.state.onChange(newFile);
    };

    onNewTestClicked = () => {
        const newFile = jsonclone(this.state.ctfFile);
        newFile.tests.push({
            id: uuid(),
            test_number: 'Untitled Test',
            description: 'No description',
            instructions: []
        });
        if (this.state.onChange) this.state.onChange(newFile);
    };

    onNewFunctionClicked = () => {
        const newFile = jsonclone(this.state.ctfFile);
        var newFuncName = 'Untitled Function';
        var counter = 1;
        while (newFile.functions[newFuncName]) {
            newFuncName = `Untitled Function (${counter})`;
            counter++;
        }
        newFile.functions[newFuncName] = {
            description: 'No description',
            varlist: [],
            instructions: []
        };
        if (this.state.onChange) this.state.onChange(newFile);
    };

    onImportsChanged = (filePath: string, imports: string[]) => {
        const newFile = jsonclone(this.state.ctfFile);
        newFile.import[filePath] = imports;
        if (this.state.onChange) this.state.onChange(newFile);
    };

    onDeleteImportFile = (filePath: string) => {
        const newFile = jsonclone(this.state.ctfFile);
        delete newFile.import[filePath];
        if (this.state.onChange) this.state.onChange(newFile);
    };


    checkallinstructionsdisabled = (test_number: string) => {

        let alltestsdisabled = false;

        if (this.state.ctfFile) {
            const ctfFile = this.state.ctfFile;

            if (ctfFile.tests) {
                ctfFile.tests.map((test: CtfTest, testindex) => {

                    if (test.test_number == test_number) {

                            let i = 0;
                            for (i = 0; i < test.instructions.length; i++) {

                                if (!test.instructions[i].hasOwnProperty("disabled")) break;
                                if (test.instructions[i].hasOwnProperty("disabled") && test.instructions[i].disabled != true)
                                    break;
                            }

                            if ( i == test.instructions.length) {
                                alltestsdisabled = true;
                            }

                    }


                }  );

            }
        }

        return alltestsdisabled;
    }

    instructionsdisabled = (test_number: string) => {

        let alltestsdisabled = this.checkallinstructionsdisabled(test_number);

        if (alltestsdisabled) {
            return 'Enable test case';
        } else {
            return 'Disable test case';
        }

    }

    getbuttonicon = (test_number: string) => {

        let alltestsdisabled = this.checkallinstructionsdisabled(test_number);

        if (alltestsdisabled) {
            return 'close-circle-o';
        } else {
            return 'check-circle-o';
        }

    }

    getstyle = (test_number: string) => {

        let alltestsdisabled = this.checkallinstructionsdisabled(test_number);

        if (alltestsdisabled) {
            return { color: "red", flex: "0 0 auto" };
        } else {
            return { color: "green", flex: "0 0 auto" };
        }

    }

    checkalltestdisabled = (test_number: string) => {

        let checked = false;

        if (this.state.ctfFile) {
            const ctfFile = this.state.ctfFile;

            if (ctfFile.tests) {
                ctfFile.tests.map((test: CtfTest, testindex) => {

                    if (test.test_number == test_number) {

                            let i = 0;
                            for (i = 0; i < test.instructions.length; i++) {

                                if (!test.instructions[i].hasOwnProperty("disabled")) break;
                                if (test.instructions[i].hasOwnProperty("disabled") && test.instructions[i].disabled != true)
                                    break;
                            }

                            if ( i == test.instructions.length) {
                                checked = true;
                            }

                    }


                }  );

            }
        }

        return checked;

    }

    onClickIcon = e => {

        if (this.state.ctfFile) {
            const ctfFile = this.state.ctfFile;

            if (ctfFile.tests) {
                ctfFile.tests.map((test: CtfTest, testindex) => {

                        if (test.test_number == e.target.id) {

                            let alltestsdisabled = this.checkallinstructionsdisabled(test.test_number);
                            let newdisable = !alltestsdisabled;

                            const newtest =  Object.assign( {}, test );

                            test.instructions.map((cmd, index) => { //instruction

                                if (cmd.hasOwnProperty("instruction") || cmd.hasOwnProperty("function") ) {
                                        const newcmd = Object.assign({}, cmd, {disabled: newdisable});

                                        newtest.instructions[index] = newcmd;
                                 }

                               }
                            );

                            this.onTestCaseChanged( testindex, newtest );

                        }

                    }
                );

            }

           e.stopPropagation();
        }

    }

    onChangeCheckbox = e => {
        if (this.state.ctfFile) {
            const ctfFile = this.state.ctfFile;

            if (ctfFile.tests) {
                ctfFile.tests.map((test: CtfTest, testindex) => {

                        if (test.test_number == e.target.name) {

                            const newtest =  Object.assign( {}, test );

                            test.instructions.map((cmd, index) => {

                                    if (cmd.hasOwnProperty("instruction")) {

                                        const newcmd = Object.assign({}, cmd, {disabled: e.target.checked});

                                        newtest.instructions[index] = newcmd;
                                    }
                                    else {  // function

                                    }

                                }
                            );

                            this.onTestCaseChanged( testindex, newtest );

                        }

                    }
                );

            }

            e.stopPropagation();
        }

    };

    reloadImports = () =>{
        const newFunctionData = this.getFunctionData()
        return newFunctionData
    }

    onDeleteRequirement = (req: string) => {
        const newFile = jsonclone(this.state.ctfFile);
        delete newFile.requirements[req]
        if (this.state.onChange) this.state.onChange(newFile);
    };

    onNewRequirementAdded = (req: string, coverage: string) => {
        const newFile = jsonclone(this.state.ctfFile);
        newFile.requirements[req] = coverage
        if (this.state.onChange)
            this.state.onChange(newFile);
    }

    onCoverageChanged = value => {
        this.setState({
            "newCoverage": value
        })
    }

    onRequirementChanged = value => {
        const newValue = value.target.value
        this.setState({
            "newRequirement": newValue
        })
    }

    componentDidMount() {
        // To disabled submit button at the beginning.
      }

    handleRequirementSubmit = () => {
        this.onNewRequirementAdded(this.state.newRequirement, this.state.newCoverage);
        this.setState({newRequirement: undefined, newCoverage: undefined})
        this.hideReqPopover();
    }

    setNewReqVisibleState = (visible) => {
        this.setState({"visible": visible });
    };

    showReqPopover = () => {
        this.setState({"visible": true });
    };

    hideReqPopover = () => {
        this.setState({"visible": false})
    }
    renderMetaData() {
        const WrappedHorizontalLoginForm = Form.create({ name: "horizontal_login" })(
            CtfFileEditor
          );
        const data = this.state.ctfFile;

        const {
            getFieldDecorator,
            getFieldsError,
            getFieldError,
            isFieldTouched
          } = this.state.form;

        return (
          <PageHeader
            title={
              <div>
                {this.state.showDirtyFlag ? "*" : ""}
                <Text
                  editable={{
                    onChange: str => this.onMetaDataChanged({ test_script_name: str })
                  }}
                >
                  {data.test_script_name}
                </Text>
              </div>
            }
            subTitle={
              <Text
                editable={{
                  onChange: str => this.onMetaDataChanged({ test_script_number: str })
                }}
              >
                {data.test_script_number}
              </Text>
            }
          >
            <Descriptions bordered>
              <Descriptions.Item key="owner" label="Owner" span={8}>
                <Text
                  editable={{
                    onChange: str => this.onMetaDataChanged({ owner: str })
                  }}
                >
                  {data.owner}
                </Text>
              </Descriptions.Item>
              <Descriptions.Item
                key="description"
                label="Description"
                span={20}
              >
                <Text
                  editable={{
                    onChange: str =>
                      this.onMetaDataChanged({ description: str })
                  }}
                >
                  {data.description}
                </Text>
              </Descriptions.Item>
              <Descriptions.Item key="setup" label="Test Setup" span={20}>
                <Text
                  editable={{
                    onChange: str => this.onMetaDataChanged({ test_setup: str })
                  }}
                >
                  {data.test_setup}
                </Text>
              </Descriptions.Item>
              <Descriptions.Item key="requirements" label="Requirements">
                {data.requirements
                  ? Object.keys(data.requirements).map((req, index) => (
                      <div key={index} >
                        {req} <Tag>{data.requirements[req]}</Tag>
                        <Tooltip title={"Delete Requirement"}>
                          <Popconfirm
                            title="Delete this requirement?"
                            placement="right"
                            icon={<Icon type="warning" />}
                            onConfirm={_ => this.onDeleteRequirement(req)}
                            okText="Delete"
                            okType="danger"
                            cancelText="Cancel"
                          >
                            <Button
                              type="link"
                              style={{ color: "gray", flex: "0 0 auto" }}
                              icon="minus-circle"
                            />
                          </Popconfirm>
                        </Tooltip>
                      </div>
                    ))
                  : null}
                <Popover
                //   placement="rightTop"
                  title="New Requirement"
                  trigger="click"
                  visible={this.state.visible}
                  onVisibleChange={this.setNewReqVisibleState}
                  content=
                  {
                  <div>
                    <Form layout="inline" ref={this.requirementsFormRef}>
                        <Form.Item>
                            <Input name="requirement"
                            prefix={
                                <Icon
                                type="check-square"
                                style={{ color: "rgba(0,0,0,.25)" }}
                                />
                            }
                            placeholder="Requirement"
                            onChange={this.onRequirementChanged}
                            defaultValue = {this.state.newRequirement? this.state.newRequirement: ""}
                            />
                        </Form.Item>
                        <Form.Item>
                                <Select style={{ width: 100 }} placeholder="Coverage"
                                onChange={this.onCoverageChanged}
                                defaultValue = {this.state.newCoverage? this.state.newCoverage: ""}
                                >
                                <Select.Option value="Full">Full</Select.Option>
                                <Select.Option value="Partial">Partial</Select.Option>
                                <Select.Option value="N/A">N/A</Select.Option>
                                </Select>
                        </Form.Item>
                        <Form.Item>
                        <Button
                            type="primary"
                            disabled={(this.state.newRequirement && this.state.newCoverage)? false: true}
                            onClick = {this.handleRequirementSubmit}
                        >
                            Add Requirement
                        </Button>
                        </Form.Item>
                    </Form>
                  </div>
                  }
                >
                <Button type="dashed" style={{ width: '160px' }}>
                    <Icon type="plus" /> Add Requirement
                </Button>
                </Popover>
              </Descriptions.Item>
            </Descriptions>
          </PageHeader>
        );
    }

    renderCtfFilePane() {

        if (this.state.ctfFile) {
            const ctfFile = this.state.ctfFile;
            return (
                <Layout>
                    {this.renderMetaData()}
                    <Content style={{ backgroundColor: 'white', overflowY: 'auto' }}>
                        <Divider>Imports</Divider>
                        {ctfFile.import && this.state.context ? (
                            Object.keys(ctfFile.import).map( (path, index) => (
                                <Row
                                    type="flex"
                                    align="middle"
                                    style={{ marginBottom: 10 }}
                                    key={index}
                                >
                                    {this.state.context.import[path] ? (
                                        <Icon
                                            type="file"
                                            style={{ fontSize: '0.8em' }}
                                        />
                                    ) : (
                                        <Tooltip
                                            title={`Unable to resolve '${path}'`}
                                        >
                                            <Icon
                                                type="warning"
                                                style={{ fontSize: '0.8em' }}
                                            />
                                        </Tooltip>
                                    )}
                                    <Text
                                        strong
                                        style={{
                                            marginLeft: 10,
                                            marginRight: 10
                                        }}
                                    >
                                        {path}
                                    </Text>
                                    <Select
                                        mode="multiple"
                                        size="small"
                                        placeholder="Select Functions"
                                        value={Object.values(ctfFile.import[path])}
                                        defaultValue={Object.values(ctfFile.import[path])}

                                        disabled={
                                            !this.state.context.import[path]
                                        }
                                        style={{ flex: '1 1 auto' }}
                                        onChange={(values: string[]) =>{
                                            this.onImportsChanged(path, values)
                                        }
                                        }
                                    >
                                        {this.state.context.import[path]
                                            ? Object.keys(
                                                  this.state.context.import[
                                                      path
                                                  ]
                                              ).map(func => (
                                                  <Select.Option
                                                      key={func}
                                                      value={func}
                                                  >
                                                      {func}
                                                  </Select.Option>
                                              ))
                                            : null}
                                    </Select>
                                    <Popconfirm
                                        title="Remove this import?"
                                        onConfirm={() =>
                                            this.onDeleteImportFile(path)
                                        }
                                    >
                                        <Button
                                            icon="delete"
                                            type="link"
                                            size="small"
                                        />
                                    </Popconfirm>
                                </Row>
                            ))
                        ) : (
                            <div />
                        )}
                        <Row type="flex" justify="end">
                            <Button
                                icon="plus"
                                size="small"
                                onClick={this.state.onAddImportFile}
                            >
                                ADD IMPORT
                            </Button>
                        </Row>
                        <Tabs defaultActiveKey="1" animated={false}>
                            <Tabs.TabPane tab="Tests" key="1">
                                <Collapse>
                                    {ctfFile.tests
                                        ? ctfFile.tests.map(
                                              (test: CtfTest, index) => (
                                                  <Panel
                                                      header={
                                                          <div
                                                            style={{display: 'flex',justifyContent: 'space-between'  }}
                                                          >
                                                           <div>
                                                            <Text
                                                              editable={{
                                                                  onChange: str =>
                                                                    {
                                                                      this.onTestCaseChanged(
                                                                          index,
                                                                          Object.assign(
                                                                              {},
                                                                              test,
                                                                              {
                                                                                test_number: str
                                                                              }
                                                                          )
                                                                      )
                                                                    }
                                                              }}
                                                            >
                                                              {test.test_number}
                                                            </Text>
                                                            </div>

                                                           <div>

                                                                <Tooltip title={this.instructionsdisabled(test.test_number)}>
                                                                        <Button
                                                                             type="link"
                                                                             style={this.getstyle(test.test_number)}
                                                                             icon= {this.getbuttonicon(test.test_number)}
                                                                             id = {test.test_number}
                                                                             onClick = {this.onClickIcon}
                                                                        />

                                                                 </Tooltip>

                                                           </div>




                                                          </div>
                                                      }
                                                      key={test.id}
                                                  >
                                                      <TestCase
                                                          test={test}
                                                          context={
                                                              this.state.context
                                                          }
                                                          droppableIdPrefix={
                                                              TEST_CASE_DROPPABLE_PREFIX
                                                          }
                                                          onChange={value =>
                                                              this.onTestCaseChanged(
                                                                  index,
                                                                  value
                                                              )
                                                          }
                                                      />
                                                      <div
                                                          style={{
                                                              display: 'flex',
                                                              justifyContent:
                                                                  'flex-end'
                                                          }}
                                                      >
                                                          <Popconfirm
                                                              title="Delete this test?"
                                                              onConfirm={() =>
                                                                  this.onDeleteTestCase(
                                                                      index
                                                                  )
                                                              }
                                                          >
                                                              <DeleteButton
                                                                  size="small"
                                                                  icon="delete"
                                                              >
                                                                  DELETE
                                                              </DeleteButton>
                                                          </Popconfirm>

                                                      </div>

                                                  </Panel>
                                              )
                                          )
                                        : null}
                                </Collapse>
                                <ButtonWithTopSpacing
                                    icon="plus"
                                    size="large"
                                    type="dashed"
                                    block
                                    onClick={this.onNewTestClicked}
                                >
                                    ADD TEST
                                </ButtonWithTopSpacing>
                            </Tabs.TabPane>
                            <Tabs.TabPane tab="Functions" key="2">
                                <Collapse>
                                    {ctfFile.functions
                                        ? Object.keys(ctfFile.functions)
                                              .sort()
                                              .map(func => (
                                                  <Panel
                                                      header={
                                                          <Text
                                                              editable={{
                                                                  onChange: str =>
                                                                      this.state
                                                                          .onRenameFunction
                                                                          ? this.state.onRenameFunction(
                                                                                func,
                                                                                str
                                                                            )
                                                                          : {}
                                                              }}
                                                          >
                                                              {func}
                                                          </Text>
                                                      }
                                                      key={func}
                                                  >
                                                      <FunctionDefinition
                                                          name={func}
                                                          func={
                                                              ctfFile.functions[
                                                                  func
                                                              ]
                                                          }
                                                          context={
                                                              this.state.context
                                                          }
                                                          droppableIdPrefix={
                                                              FUNCTION_DEF_DROPPABLE_PREFIX
                                                          }
                                                          onChange={value =>
                                                              this.onFunctionDefChanged(
                                                                  func,
                                                                  value
                                                              )
                                                          }
                                                      />
                                                      <div
                                                          style={{
                                                              display: 'flex',
                                                              justifyContent:
                                                                  'flex-end'
                                                          }}
                                                      >
                                                          <Popconfirm
                                                              title="Delete this function?"
                                                              onConfirm={() =>
                                                                  this.onDeleteFunction(
                                                                      func
                                                                  )
                                                              }
                                                          >
                                                              <DeleteButton
                                                                  size="small"
                                                                  icon="delete"
                                                              >
                                                                  DELETE
                                                              </DeleteButton>
                                                          </Popconfirm>
                                                      </div>
                                                  </Panel>
                                              ))
                                        : null}
                                </Collapse>
                                <ButtonWithTopSpacing
                                    icon="plus"
                                    size="large"
                                    type="dashed"
                                    block
                                    onClick={this.onNewFunctionClicked}
                                >
                                    ADD FUNCTION
                                </ButtonWithTopSpacing>
                            </Tabs.TabPane>
                        </Tabs>
                    </Content>
                </Layout>
            );
        } else {
            return <Empty />;
        }
    }

    getFunctionData = () => {
        var newFunctionData: LibraryGroup[] = this.state.context
            ? this.state.context.functions.reduce(
                  (groups: LibraryGroup[], editingData) => {
                      const groupName = editingData.src
                          ? editingData.src
                          : LOCAL_FUNCTION_GROUP_NAME;
                      if (!groups.find(g => g.name === groupName))
                          groups.push({ name: groupName, elements: [] });
                      groups
                          .find(g => g.name === groupName)
                          .elements.push({
                              name: editingData.name,
                              description: editingData.function.description
                          });
                      return groups;
                  },
                  []
              )
            : [];
        return newFunctionData
    }

    render() {
        const functionData = this.reloadImports()
        const pluginData = this.state.context
            ? this.state.context.plugins.map(p => {
                  return {
                      name: p.group_name,
                      elements: p.instructions.map(c => ({
                          name: c.name,
                          description: c.description
                      }))
                  };
              })
            : [];
        return (
            <DragDropContext onDragEnd={this.onDrop}>
                <Layout
                    style={{
                        padding: '0px 24px 0px 24px',
                    }}
                >
                    <Content
                        style={{
                            background: '#fff',
                            padding: 24,
                            margin: '0 0 0 0',
                            overflowY: 'auto'
                        }}
                    >
                        {this.renderCtfFilePane()}
                    </Content>
                </Layout>
                <Sider
                    width={300}
                    style={{ overflowX: 'auto' , overflowY: 'auto'}}
                    theme={'light'}
                    reverseArrow={true}
                >
                    <LibraryPane
                        title={'CTF Instructions'}
                        data={pluginData}
                        droppableIdPrefix={COMMAND_LIB_DROPPABLE_PREFIX}
                    />
                    <LibraryPane
                        title={'CTF Functions'}
                        data={functionData}
                        droppableIdPrefix={FUNCTION_LIB_DROPPABLE_PREFIX}
                    />
                </Sider>
            </DragDropContext>
        );
    }
}

export const CtfFileEditorInst = Form.create<EditorProps>({})(CtfFileEditor);
