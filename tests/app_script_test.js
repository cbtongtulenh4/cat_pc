/***********************
 * MAIN GET API
 ***********************/

// https://script.google.com/macros/s/AKfycbz263EEntoO4AoK02NuT0noLLzIdz2x5SjtTBpr_tmGzbDoFqnEpB3l5j8t7flTznyffw/exec

function doGet(e) {
    var params = e.parameter;
    var mode = params.mode || "full"; // full | time_only

    var sheet = SpreadsheetApp
        .openById("16ZlvTXpnwOavkj38sfPt68Oz9jsiWkVgAKYEQ9QwsE8")
        .getSheets()[0];

    var data = sheet.getRange("B:B").getValues(); // KEY ở cột B

    for (var i = 0; i < data.length; i++) {
        if (!data[i][0]) break;

        if (data[i][0] == params.key) {
            var result = is_valid(sheet, params, i + 1, mode);
            return ContentService.createTextOutput(JSON.stringify(result));
        }
    }

    return ContentService.createTextOutput(
        JSON.stringify({ status: false, message: "KEY INVALID. !!!" })
    );
}

/***********************
 * VALIDATION LOGIC
 ***********************/
function is_valid(sheet, params, row, mode) {

    // Count request
    var requestCntCell = sheet.getRange(row, 9); // column I
    requestCntCell.setValue(requestCntCell.getValue() + 1);

    var statusCell = sheet.getRange(row, 8); // column H
    var status = statusCell.getValue();

    // BLOCK DIE
    if (status === "DIE") {
        return {
            status: false,
            message: "Your account has been locked!!! Please contact the developer."
        };
    }
    // ===== CHECK TIME (COMMON) =====
    var expireTime = sheet.getRange(row, 4).getValue(); // column D
    if (
        expireTime !== "" &&
        !is_time_valid(expireTime.getTime(), new Date().getTime())
    ) {
        sheet.getRange(row, 10).setValue("time limit"); // column J
        statusCell.setValue("DIE");
        return {
            status: false,
            message: `Your account has expired. !!! (${expireTime})`
        };
    }

    // ===== MODE: FULL =====
    var total_acc = sheet.getRange(row, 6).getValue(); // column F
    var colL = sheet.getRange(row, 12).getValue(); // column L

    // First activation
    if (status.trim() === "") {
        statusCell.setValue("LIVE");

        var foreignKey = gen_key();
        sheet.getRange(row, 3).setValue(foreignKey); // column C
        sheet.getRange(row, 7).setValue(params.pc_info); // column G
        sheet.getRange(row, 11).setValue(0); // column K

        return {
            status: true,
            message: "Account activated successfully. !!!",
            foreign_key: foreignKey,
            total_acc: total_acc,
            user: colL
        };
    }

    // PC INFO CHECK
    if (params.pc_info != sheet.getRange(row, 7).getValue()) {
        sheet.getRange(row, 10).setValue("different pc_info " + params.pc_info);
        statusCell.setValue("DIE");
        return {
            status: false,
            message: "You have violated the policy!!!"
        };
    }

    // FOREIGN KEY CHECK
    if (params.foreign_key != sheet.getRange(row, 3).getValue()) {
        sheet.getRange(row, 10).setValue(
            "different foreign key " + params.foreign_key
        );
        statusCell.setValue("DIE");
        return {
            status: false,
            message: "You have violated the policy!!!"
        };
    }

    // ===== MODE: TIME ONLY =====
    if (mode === "time_only") {
        return {
            status: true,
            message: "Login success. !!!",
            user: colL
        };
    }

    // SERVER ACC LIMIT CHECK
    if (sheet.getRange(row, 11).getValue() > params.acc_limit) {
        sheet.getRange(row, 10).setValue("acc limit server");
        statusCell.setValue("DIE");
        return {
            status: false,
            message: "You have violated the policy!!!"
        };
    }

    // CLIENT ACC LIMIT CHECK
    var acc_limit = sheet.getRange(row, 6).getValue();
    if (acc_limit > 0 && acc_limit <= params.acc_limit) {
        sheet.getRange(row, 10).setValue("acc limit");
        statusCell.setValue("DIE");
        return {
            status: false,
            message: `The account has exceeded the registration limit. !!! (${acc_limit})`
        };
    }

    return {
        status: true,
        message: "Login success. !!!",
        total_acc: total_acc,
        user: colL
    };
}

/***********************
 * POST API (UPDATE ACC LIMIT)
 ***********************/
function doPost(e) {
    var params = e.parameter;
    var sheet = SpreadsheetApp
        .openById("1ttAM7QCPdmLXo2xxy0P2dLIj2Jpw9JoOOi70tCOVBmA")
        .getSheets()[0];

    var data = sheet.getRange("B:B").getValues();
    var message = { status: false, message: "KEY INVALID. !!!" };

    for (var i = 0; i < data.length; i++) {
        if (!data[i][0]) break;

        if (data[i][0] == params.key) {
            var row = i + 1;

            if (sheet.getRange(row, 11).getValue() > params.acc_limit) {
                sheet
                    .getRange(row, 10)
                    .setValue(
                        `acc limit server: ${sheet.getRange(row, 11).getValue()} > ${params.acc_limit}`
                    );
                sheet.getRange(row, 8).setValue("DIE");

                message = {
                    status: false,
                    message: "You have violated the policy!!!"
                };
                break;
            }

            sheet.getRange(row, 11).setValue(params.acc_limit);
            message = { status: true, message: "KEY UPDATED VALUE. !!!" };
            break;
        }
    }

    return ContentService.createTextOutput(JSON.stringify(message));
}

/***********************
 * UTILITIES
 ***********************/
function is_time_valid(limit_time, request_time) {
    return limit_time >= request_time;
}

function gen_key() {
    return (
        Math.random().toString(36).substring(2, 15) +
        Math.random().toString(36).substring(2, 15)
    );
}

/***********************
 * TEST POST
 ***********************/
function testDoPost() {
    var mockEvent = {
        parameter: {
            key: "13ZU5BmRGfOIUkqwNrzw4sl0cBL8VVWQ",
            pc_info: "PF3F82QT",
            foreign_key: "tYawQdd89iOVaZBTv5dVZSU2kOEhYbZR",
            acc_limit: "1000"
        }
    };

    var result = doPost(mockEvent);
    Logger.log(result.getContent());
}

/***********************
 * TEST TIME ONLY
 ***********************/
function testDoGetTimeOnly() {
    var mockEvent = {
        parameter: { 'key': 'gyDedTd89iOVaZBTv5d12342kOEhIje4', 'acc_limit': 0, 'foreign_key': 't3p64xzxoxlyyy1klcjgaf', 'pc_info': 'PF3F82QT|6CBAC34C-2C57-11B2-A85C-A5534000A869|178BFBFF00860F81|ACE4_2E00_1A86_F00E_2EE4_AC00_0000_0001.', 'mode': 'time_only' }
    };

    var result = doGet(mockEvent);
    Logger.log(result.getContent());
}