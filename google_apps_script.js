/**
 * =========================================================================
 * WEST BENGAL ARD DEPARTMENT - INTERACTIVE SMART POSTING BOARD
 * Google Apps Script Companion for Google Sheets (Dashboard Edition)
 * 
 * INSTRUCTIONS:
 * 1. Open your uploaded Google Sheet: WB_ARD_Interactive_Posting_Board_GoogleSheets_Ready.xlsx
 * 2. Click on "Extensions" -> "Apps Script" in the top menu.
 * 3. Delete any code in the editor and paste the ENTIRE contents of this file.
 * 4. Click the disk icon (Save), then reload your Google Sheet.
 * 5. A new menu "🏛️ ARD Secretariat Board" will appear in your sheet toolbar!
 * =========================================================================
 */

function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('🏛️ ARD Secretariat Board')
    .addItem('⚡ Scan Collisions & Displacement Conflicts', 'scanCollisions')
    .addItem('🔄 Prune Dropdowns (Hide Already Allotted Posts)', 'pruneAvailableDropdowns')
    .addSeparator()
    .addItem('🔑 Configure Google AI Studio Gemini API Key', 'setGeminiApiKey')
    .addItem('✨ Run AI Auto-Allotment with Gemini Flash (Google AI Studio)', 'runGeminiAutoAllot')
    .addSeparator()
    .addItem('📄 Export Secretariat Order to Official Google Doc', 'exportToGoogleDoc')
    .addToUi();
}

/**
 * Real-Time onEdit Trigger:
/**
 * Real-Time onEdit Trigger:
 * Fires instantly when an officer selects a post.
 * Alerts immediately if the post has already been allotted elsewhere,
 * and dynamically colors the cell/row based on vacancy type and status:
 * - Green (#D1FAE5): Pure Vacancy / Direct Allotment
 * - Soft Blue / Amber (#DBEAFE / #FEF3C7): Allotted with Service Utilization (SU)
 * - Red (#FFE4E6): Conflict / Duplicate Allotment / Attention Required
 */
function onEdit(e) {
  if (!e || !e.range) return;
  const sheet = e.range.getSheet();
  const sName = sheet.getName();
  if (sName !== 'Posting_Dashboard' && sName !== '50_Pt_Roster_Decisions') return;
  
  const col = e.range.getColumn();
  const row = e.range.getRow();
  
  // Handle 50_Pt_Roster_Decisions (Col 13 = Substantive, Col 15 = SU)
  // Handle Posting_Dashboard (Col 10 = Substantive, Col 12 = SU)
  const isRosterSheet = sName === '50_Pt_Roster_Decisions';
  const subCol = isRosterSheet ? 13 : 10;
  const suCol = isRosterSheet ? 15 : 12;
  const startRow = isRosterSheet ? 2 : 10;
  
  if ((col === subCol || col === suCol) && row >= startRow) {
    const val = e.range.getValue();
    if (!val || val.toString().trim() === '') {
      e.range.setBackground('#FFFFFF');
      return;
    }
    const postStr = val.toString().trim();
    
    const lastRow = sheet.getLastRow();
    const subValues = sheet.getRange(startRow, subCol, lastRow - startRow + 1, 1).getValues();
    const suValues = sheet.getRange(startRow, suCol, lastRow - startRow + 1, 1).getValues();
    
    let count = 0;
    for (let i = 0; i < subValues.length; i++) {
      if (subValues[i][0] && subValues[i][0].toString().trim() === postStr) count++;
      if (suValues[i][0] && suValues[i][0].toString().trim() === postStr) count++;
    }
    
    if (count > 1) {
      e.range.setBackground('#FFE4E6'); // Soft Red
      SpreadsheetApp.getActiveSpreadsheet().toast(
        `⚠️ WARNING: Post "${postStr}" is already allotted in ${count} places! Please select an unoccupied vacancy.`,
        'Duplicate Post Alert',
        8
      );
    } else {
      if (col === subCol) {
        e.range.setBackground('#D1FAE5'); // Pure Vacancy Green
      } else {
        e.range.setBackground('#DBEAFE'); // SU Blue
      }
    }
  }
}

/**
 * 1. SCAN FOR ALLOTMENT COLLISIONS & DISPLACEMENT CONFLICTS
 */
function scanCollisions() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const dashSheet = ss.getSheetByName('Posting_Dashboard');
  const suSheet = ss.getSheetByName('All_Cadre_Posts_1794');

  if (!dashSheet || !suSheet) {
    SpreadsheetApp.getUi().alert('Error: Required sheets not found.');
    return;
  }

  const lastRow = dashSheet.getLastRow();
  if (lastRow < 10) return;

  const dashData = dashSheet.getRange(10, 1, lastRow - 9, 17).getValues();
  const substantiveCounts = {};
  const duplicatePosts = [];
  const suCollisions = [];

  // Build Cadre occupancy map from All_Cadre_Posts_1794
  const suLastRow = suSheet.getLastRow();
  const suData = suSheet.getRange(2, 1, suLastRow - 1, 4).getValues();
  const suOccupancyMap = {};
  for (let i = 0; i < suData.length; i++) {
    const postLabel = suData[i][0];
    const status = suData[i][2]; // 'Clear Vacancy' or 'Occupied'
    const incumbent = suData[i][3];
    suOccupancyMap[postLabel] = { status: status, incumbent: incumbent };
  }

  for (let i = 0; i < dashData.length; i++) {
    const sl = dashData[i][0];
    const name = dashData[i][3]; // Col D (index 3)
    const subPost = dashData[i][9]; // Col J (index 9)
    const enableSU = dashData[i][10]; // Col K (index 10)
    const suPost = dashData[i][11]; // Col L (index 11)

    if (subPost && subPost.toString().trim() !== '') {
      const p = subPost.toString().trim();
      substantiveCounts[p] = (substantiveCounts[p] || []);
      substantiveCounts[p].push(`Sl ${sl}: ${name}`);
    }

    if (enableSU === 'YES' && suPost && suPost.toString().trim() !== '') {
      const match = suOccupancyMap[suPost.toString().trim()];
      if (match && match.status === 'Occupied') {
        suCollisions.push(`• Sl ${sl}: ${name} -> SU Post "${suPost}" DISPLACES: ${match.incumbent} (Eligible for Transfer due to Displacement)`);
      }
    }
  }

  for (const post in substantiveCounts) {
    if (substantiveCounts[post].length > 1) {
      duplicatePosts.push(`• Post "${post}" was allotted to multiple officers: ${substantiveCounts[post].join(' AND ')}`);
    }
  }

  let report = '=== 🏛️ ARD POSTING AUDIT REPORT ===\n\n';
  if (duplicatePosts.length === 0 && suCollisions.length === 0) {
    report += '✅ NO CONFLICTS FOUND!\nAll allotted posts are uniquely assigned and no unhandled collisions detected.';
  } else {
    if (duplicatePosts.length > 0) {
      report += `⚠️ DUPLICATE SUBSTANTIVE ALLOTMENTS (${duplicatePosts.length}):\n` + duplicatePosts.join('\n') + '\n\n';
    }
    if (suCollisions.length > 0) {
      report += `⚠️ SERVICE UTILIZATION COLLISIONS (${suCollisions.length}):\n` + suCollisions.join('\n') + '\n\n';
      report += 'These incumbent officers are now MARKED AS ELIGIBLE FOR TRANSFER DUE TO DISPLACEMENT and can be re-allocated in Section 3 of Posting_Dashboard.';
    }
  }

  SpreadsheetApp.getUi().alert(report);
}

/**
 * 2. PRUNE DROPDOWNS: Only show unallotted posts in dropdowns
 */
function pruneAvailableDropdowns() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const dashSheet = ss.getSheetByName('Posting_Dashboard');
  const ddSheet = ss.getSheetByName('Available_DD_Posts');
  const suSheet = ss.getSheetByName('All_Cadre_Posts_1794');

  if (!dashSheet || !ddSheet || !suSheet) {
    SpreadsheetApp.getUi().alert('Required sheets not found.');
    return;
  }

  const dashLastRow = dashSheet.getLastRow();
  const allocatedPosts = new Set();

  if (dashLastRow >= 10) {
    // Read both Column J (Col 10: Substantive) AND Column L (Col 12: Service Utilization)
    const colJ = dashSheet.getRange(10, 10, dashLastRow - 9, 1).getValues();
    const colL = dashSheet.getRange(10, 12, dashLastRow - 9, 1).getValues();
    for (let i = 0; i < colJ.length; i++) {
      if (colJ[i][0] && colJ[i][0].toString().trim() !== '') {
        allocatedPosts.add(colJ[i][0].toString().trim());
      }
      if (colL[i][0] && colL[i][0].toString().trim() !== '') {
        allocatedPosts.add(colL[i][0].toString().trim());
      }
    }
  }

  // 1. Prune DD Posts for Column J (Substantive Dropdown)
  const ddLastRow = ddSheet.getLastRow();
  const allDD = ddSheet.getRange(2, 2, ddLastRow - 1, 1).getValues();
  const availableDD = [];
  for (let i = 0; i < allDD.length; i++) {
    const p = allDD[i][0];
    if (p && !allocatedPosts.has(p.toString().trim())) {
      availableDD.push(p);
    }
  }

  // 2. Prune Cadre Posts for Column L (Service Utilization Dropdown)
  const suLastRow = suSheet.getLastRow();
  const allSU = suSheet.getRange(2, 1, suLastRow - 1, 1).getValues();
  const availableSU = [];
  for (let i = 0; i < allSU.length; i++) {
    const p = allSU[i][0];
    if (p && !allocatedPosts.has(p.toString().trim())) {
      availableSU.push(p);
    }
  }

  // Create or update a hidden pruned list sheet
  let prunedSheet = ss.getSheetByName('_Pruned_Lists');
  if (!prunedSheet) {
    prunedSheet = ss.insertSheet('_Pruned_Lists');
    prunedSheet.hideSheet();
  } else {
    prunedSheet.clear();
  }

  if (availableDD.length > 0) {
    prunedSheet.getRange(1, 1, availableDD.length, 1).setValues(availableDD.map(item => [item]));
    const ruleDD = SpreadsheetApp.newDataValidation()
      .requireValueInRange(prunedSheet.getRange(1, 1, availableDD.length, 1))
      .setAllowInvalid(true)
      .build();
    dashSheet.getRange(10, 10, 242, 1).setDataValidation(ruleDD);
  }

  if (availableSU.length > 0) {
    prunedSheet.getRange(1, 2, availableSU.length, 1).setValues(availableSU.map(item => [item]));
    const ruleSU = SpreadsheetApp.newDataValidation()
      .requireValueInRange(prunedSheet.getRange(1, 2, availableSU.length, 1))
      .setAllowInvalid(true)
      .build();
    dashSheet.getRange(10, 12, dashLastRow - 9, 1).setDataValidation(ruleSU);
  }

  SpreadsheetApp.getUi().alert(
    `✅ Dropdowns Pruned Successfully!\n\n` +
    `• Substantive DD Posts Active: ${availableDD.length} remaining\n` +
    `• Service Utilization Posts Active: ${availableSU.length} remaining\n\n` +
    `Posts used anywhere in Column J or Column L are now hidden from all dropdowns!`
  );
}

/**
 * 3. CONFIGURE GOOGLE AI STUDIO GEMINI API KEY
 */
function setGeminiApiKey() {
  const ui = SpreadsheetApp.getUi();
  const response = ui.prompt(
    'Google AI Studio Gemini API Key',
    'Enter your Gemini API Key from Google AI Studio (https://aistudio.google.com/):',
    ui.ButtonSet.OK_CANCEL
  );

  if (response.getSelectedButton() === ui.Button.OK) {
    const key = response.getResponseText().trim();
    if (key) {
      PropertiesService.getUserProperties().setProperty('GEMINI_API_KEY', key);
      ui.alert('✅ Gemini API Key saved securely to your Google Account!');
    } else {
      ui.alert('API Key cannot be empty.');
    }
  }
}

/**
 * 4. RUN AI AUTO-ALLOTMENT WITH GEMINI FLASH (GOOGLE AI STUDIO)
 */
function runGeminiAutoAllot() {
  const apiKey = PropertiesService.getUserProperties().getProperty('GEMINI_API_KEY');
  const ui = SpreadsheetApp.getUi();

  if (!apiKey) {
    ui.alert('Please configure your Google AI Studio Gemini API Key first via:\n🏛️ ARD Secretariat Board -> 🔑 Configure Google AI Studio Gemini API Key');
    return;
  }

  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const dashSheet = ss.getSheetByName('Posting_Dashboard');
  const ddSheet = ss.getSheetByName('Available_DD_Posts');

  const ddLast = ddSheet.getLastRow();

  // Find unallotted candidates in Section 1 (rows 10 to 251)
  const rosterData = dashSheet.getRange(10, 1, 242, 10).getValues();
  const pendingIndices = [];

  for (let i = 0; i < rosterData.length; i++) {
    const subPost = rosterData[i][9]; // Col J (index 9)
    if (!subPost || subPost.toString().trim() === '') {
      pendingIndices.push(i);
      if (pendingIndices.length >= 10) break; // Process in batches of 10
    }
  }

  if (pendingIndices.length === 0) {
    ui.alert('All candidates already have substantive posts assigned!');
    return;
  }

  // Get currently available posts
  const allocatedSet = new Set();
  for (let i = 0; i < rosterData.length; i++) {
    if (rosterData[i][9]) allocatedSet.add(rosterData[i][9].toString().trim());
  }

  const ddData = ddSheet.getRange(2, 2, ddLast - 1, 3).getValues(); // Post Label, Estab, Dist
  const availableDD = [];
  for (let i = 0; i < ddData.length; i++) {
    const label = ddData[i][0].toString().trim();
    if (!allocatedSet.has(label)) {
      availableDD.push({ label: label, dist: ddData[i][2] });
    }
  }

  ui.alert(`🤖 Gemini AI Studio Assistant will now optimize and allot the next ${pendingIndices.length} candidates.\n\nClick OK to proceed.`);

  let successCount = 0;
  for (let idx of pendingIndices) {
    const candidate = {
      sl: rosterData[idx][0],
      name: rosterData[idx][3], // Col D (index 3)
      presentDist: rosterData[idx][6], // Col G (index 6)
      dor: rosterData[idx][7], // Col H (index 7)
      prefs: rosterData[idx][8] // Col I (index 8)
    };

    const prompt = `You are the Senior Cadre Allotment Officer for the Animal Resources Development Department, Government of West Bengal.
Candidate: ${candidate.name} (Sl: ${candidate.sl})
Present District: ${candidate.presentDist}
Date of Superannuation: ${candidate.dor}
Stated Preferences: ${candidate.prefs}

Available Unblocked Deputy Director Posts:
${JSON.stringify(availableDD.slice(0, 40))}

Rule: Prioritize stated preferences first. If not available, prioritize same or nearby district (${candidate.presentDist}).
Return ONLY a valid JSON with format:
{"chosen_post_label": "exact post label string from list", "justification": "short reason"}`;

    try {
      const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`;
      const payload = {
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: { responseMimeType: "application/json" }
      };

      const options = {
        method: "post",
        contentType: "application/json",
        payload: JSON.stringify(payload),
        muteHttpExceptions: true
      };

      const res = UrlFetchApp.fetch(url, options);
      if (res.getResponseCode() === 200) {
        const jsonRes = JSON.parse(res.getContentText());
        const candidateOutput = jsonRes.candidates[0].content.parts[0].text;
        const parsed = JSON.parse(candidateOutput);

        if (parsed.chosen_post_label) {
          // Write to Col J (10th column) of Posting_Dashboard
          dashSheet.getRange(idx + 10, 10).setValue(parsed.chosen_post_label);
          allocatedSet.add(parsed.chosen_post_label);
          const aIdx = availableDD.findIndex(p => p.label === parsed.chosen_post_label);
          if (aIdx >= 0) availableDD.splice(aIdx, 1);
          successCount++;
        }
      }
    } catch (e) {
      Logger.log("Gemini error: " + e);
    }
  }

  ui.alert(`✅ Gemini Auto-Allotment Finished!\n\nSuccessfully allotted ${successCount} candidates. Run again to process the next batch or inspect the choices in 'Posting_Dashboard'.`);
}

/**
 * 5. EXPORT SECRETARIAT ORDER TO GOOGLE DOC
 */
function exportToGoogleDoc() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const orderSheet = ss.getSheetByName('Secretariat_Posting_Order');

  if (!orderSheet) {
    SpreadsheetApp.getUi().alert('Error: Secretariat_Posting_Order sheet not found.');
    return;
  }

  const lastRow = orderSheet.getLastRow();
  if (lastRow < 7) {
    SpreadsheetApp.getUi().alert('No order data found.');
    return;
  }

  const doc = DocumentApp.create('WB_ARD_Secretariat_Notification_Order_Memo_391');
  const body = doc.getBody();

  // Secretariat Masthead
  const title1 = body.appendParagraph('GOVERNMENT OF WEST BENGAL');
  title1.setHeading(DocumentApp.ParagraphHeading.HEADING1).setAlignment(DocumentApp.HorizontalAlignment.CENTER);
  
  const title2 = body.appendParagraph('Animal Resources Development Department\nAR & AH Branch, Prani Sampad Bhawan, LB-2, Sector-III, Salt Lake, Kolkata - 700 106');
  title2.setAlignment(DocumentApp.HorizontalAlignment.CENTER);

  const memoPara = body.appendParagraph('\nNo. 1890-AR&AH/3A-16/2026                                                                    Date: 12.09.2026');
  memoPara.setBold(true);

  const notifHeader = body.appendParagraph('\nNOTIFICATION\n');
  notifHeader.setHeading(DocumentApp.ParagraphHeading.HEADING2).setAlignment(DocumentApp.HorizontalAlignment.CENTER);

  const preamble = body.appendParagraph(
    'The Governor is pleased to appoint / promote / transfer the following officers borne under the West Bengal Animal Husbandry & Veterinary Service to the posts mentioned against their names on promotion / transfer / placement of service in the Pay Level indicated under WBS (ROPA) Rules, 2019 with effect from the date of taking over charge of their respective posts under the Directorate of Animal Resources & Animal Health, West Bengal. Their places of posting are mentioned below:\n'
  );

  // Table Schedule
  const data = orderSheet.getRange(6, 1, lastRow - 5, 6).getValues();
  const table = body.appendTable(data);
  table.setBorderWidth(1);

  // Format header row
  const headerRow = table.getRow(0);
  for (let c = 0; c < 6; c++) {
    headerRow.getCell(c).setBackgroundColor('#1E3A8A').getChild(0).asParagraph().setFontColor('#FFFFFF').setBold(true);
  }

  const closing = body.appendParagraph('\nThis appointment / transfer is made in the interest of public service.\n\n');
  closing.setItalic(true);

  const sig = body.appendParagraph('By order of the Governor,\n\nSd/-\nSpecial Secretary to the Government of West Bengal\n');
  sig.setAlignment(DocumentApp.HorizontalAlignment.RIGHT);

  doc.saveAndClose();

  const url = doc.getUrl();
  SpreadsheetApp.getUi().alert(`✅ Official Secretariat Order Generated!\n\nDocument URL:\n${url}\n\nClick OK and open your Google Drive to view or print the document.`);
}
