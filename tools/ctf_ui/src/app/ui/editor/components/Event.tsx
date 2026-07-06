/*
# =========================================================================================
# MSC-26646-1, "Core Flight System Test Framework (CTF)"
#
# This software is governed by the NASA Open Source Agreement (NOSA) License and may be used,
# distributed and modified only pursuant to the terms of that agreement.
# See the License for the specific language governing permissions and limitations under the
# License at https://software.nasa.gov/ .
#
# Unless required by applicable law or agreed to in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either expressed or implied.
#
# Copyright © 2019-2026 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration. All Rights Reserved.
#
# File: Event.tsx
#
# Purpose: This file defines Event header.
#
# Note: This file was created at the NASA Johnson Space Center.
# =========================================================================================
*/

import * as React from "react";
import {
    CtfFunctionCall,
    CtfInstruction
} from "../../../../model/ctf-file";
import { EditingContext } from "../../../../model/editing-context";
import { CommandOrFunctionCall } from "./CommandOrFunctionCall";