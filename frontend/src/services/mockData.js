// PharmMedian Standalone Mock Data Store with LocalStorage Persistence

const STORAGE_KEY = 'pharmmedian_mock_db_v2';

export const initialMockDB = {
  currentUser: {
    id: 1,
    username: 'pharmacy_admin',
    email: 'indiranagar@medplus.com',
    role: 'PHARMACY',
    organization_name: 'MedPlus Central Indiranagar',
  },
  users: {
    PHARMACY: { id: 1, username: 'pharmacy_admin', email: 'indiranagar@medplus.com', role: 'PHARMACY', organization_name: 'MedPlus Central Indiranagar' },
    DISTRIBUTOR: { id: 3, username: 'bluedart_logistics', email: 'dispatch@bluedart.com', role: 'DISTRIBUTOR', organization_name: 'BlueDart Pharma Logistics' },
    MANUFACTURER: { id: 2, username: 'sun_pharma', email: 'compliance@sunpharma.com', role: 'MANUFACTURER', organization_name: 'Sun Pharma Laboratories' },
    FACILITY: { id: 4, username: 'bioclean_waste', email: 'ops@biocleanwaste.com', role: 'FACILITY', organization_name: 'BioClean Waste Disposal Facility' },
    REGULATOR: { id: 5, username: 'cdsco_inspector', email: 'audit@cdsco.gov.in', role: 'REGULATOR', organization_name: 'CDSCO Regulatory Body' },
  },
  batches: [
    {
      id: 1,
      batch_number: 'BATCH-001',
      medicine_name: 'Augmentin Duo 625mg',
      brand_name: 'Augmentin Duo',
      generic_name: 'Amoxicillin & Potassium Clavulanate',
      strength: '625mg',
      quantity: 100,
      quantity_to_destroy: 100,
      expiry_date: '2026-08-30',
      expiry_status: 'EXPIRED',
      current_status: 'EXPIRED',
      current_location: 'MedPlus Central Indiranagar Shelf B4',
      reverse_chain_flag: true,
      destruction_status: null,
      scheduled_status: 'PENDING',
      scheduled_date: null,
    },
    {
      id: 2,
      batch_number: 'BATCH-002',
      medicine_name: 'Dolo 650mg Paracetamol',
      brand_name: 'Dolo 650',
      generic_name: 'Paracetamol',
      strength: '650mg',
      quantity: 500,
      quantity_to_destroy: 500,
      expiry_date: '2026-11-15',
      expiry_status: 'EXPIRING_SOON',
      current_status: 'ACTIVE',
      current_location: 'MedPlus Koramangala Warehouse',
      reverse_chain_flag: false,
      destruction_status: null,
      scheduled_status: 'PENDING',
      scheduled_date: null,
    },
    {
      id: 3,
      batch_number: 'BATCH-003',
      medicine_name: 'Pan 40 Gastro-Resistant',
      brand_name: 'Pan 40',
      generic_name: 'Pantoprazole Sodium',
      strength: '40mg',
      quantity: 250,
      quantity_to_destroy: 250,
      expiry_date: '2027-04-20',
      expiry_status: 'ACTIVE',
      current_status: 'ACTIVE',
      current_location: 'BlueDart Logistics Depot #4',
      reverse_chain_flag: false,
      destruction_status: null,
      scheduled_status: 'PENDING',
      scheduled_date: null,
    },
    {
      id: 4,
      batch_number: 'BATCH-004',
      medicine_name: 'Azithral 500mg Tablet',
      brand_name: 'Azithral 500',
      generic_name: 'Azithromycin',
      strength: '500mg',
      quantity: 150,
      quantity_to_destroy: 150,
      expiry_date: '2026-05-10',
      expiry_status: 'EXPIRED',
      current_status: 'DESTROYED',
      current_location: 'BioClean Incineration Chamber #2',
      reverse_chain_flag: true,
      destruction_status: 'DESTROYED',
      scheduled_status: 'COMPLETED',
      scheduled_date: '2026-06-01',
    },
  ],
  returnRequests: [],
  disputes: [],
  handoffs: [],
  destructionRecords: [],
  certificates: [],
  workflowEvents: [
    {
      id: 101,
      batch_id: 1,
      event_type: 'EXPIRY_FLAGGED',
      from_status: 'ACTIVE',
      to_status: 'EXPIRED',
      actor_id: 1,
      actor_name: 'MedPlus Central Indiranagar',
      actor_role: 'PHARMACY',
      data: { note: 'Automated shelf inventory expiry scanning threshold reached.' },
      created_at: new Date(Date.now() - 3600000 * 4).toISOString(),
      time_display: '09:15',
    },
  ],
  moderatorEvents: [
    {
      id: 201,
      workflow_event_id: 101,
      batch_id: 1,
      risk_level: 'MEDIUM',
      analysis: 'Batch BATCH-001 flagged as EXPIRED. Quantity 100 units requires quarantine and initiation of reverse supply chain return workflow to prevent accidental dispensation.',
      recommended_action: 'Pharmacy staff should initiate return request immediately and attach photographic proof of package seal.',
      message: 'Automated AI Moderator alert: Expiry detected for Augmentin Duo 625mg. Quarantine confirmed.',
    },
  ],
  alerts: [
    {
      id: 301,
      batch_id: 1,
      severity: 'MEDIUM',
      title: 'INVENTORY_EXPIRY_WARNING',
      description: 'Batch BATCH-001 (Augmentin Duo 625mg) expired on 2026-08-30. 100 units flagged for return.',
      is_acknowledged: false,
      created_at: new Date(Date.now() - 3600000 * 4).toISOString(),
      time_display: '09:15',
    },
  ],
  notifications: [
    {
      id: 401,
      user_id: 1,
      title: 'Expiry Alert',
      message: 'Batch BATCH-001 (Augmentin Duo 625mg) has expired. Please initiate return request.',
      read_status: false,
      created_at: new Date(Date.now() - 3600000 * 4).toISOString(),
    },
  ],
  reallocationRecommendations: [
    {
      id: 'REC-001',
      medicine_name: 'Dolo 650mg Paracetamol',
      source_pharmacy: 'MedPlus Koramangala (Surplus Stock)',
      target_pharmacy: 'Apollo Pharmacy Indiranagar (Stock Out Risk)',
      batch_number: 'BATCH-002',
      quantity_to_transfer: 200,
      days_to_expiry: 65,
      urgency: 'HIGH',
      estimated_waste_saved_value: 4800.0,
      reasoning: 'Apollo Indiranagar is experiencing high sales velocity (45 units/day) with only 3 days stock remaining. MedPlus Koramangala holds 500 surplus units expiring in 65 days.',
    },
    {
      id: 'REC-002',
      medicine_name: 'Pan 40 Gastro-Resistant',
      source_pharmacy: 'Frank Ross Pharmacy MG Road',
      target_pharmacy: 'MedPlus Central Indiranagar',
      batch_number: 'BATCH-003',
      quantity_to_transfer: 100,
      days_to_expiry: 88,
      urgency: 'MEDIUM',
      estimated_waste_saved_value: 3200.0,
      reasoning: 'Rebalancing inventory to prevent near-expiry return costs.',
    },
  ],
  reallocationRawData: {
    demand_data: [
      {
        pharmacy_name: 'Apollo Pharmacy Indiranagar',
        medicine_name: 'Dolo 650mg Paracetamol',
        current_stock: 12,
        daily_sales_rate: 45,
        days_of_stock: 0.3,
      },
      {
        pharmacy_name: 'Wellness Forever HSR Layout',
        medicine_name: 'Augmentin Duo 625mg',
        current_stock: 18,
        daily_sales_rate: 15,
        days_of_stock: 1.2,
      },
      {
        pharmacy_name: 'MedPlus Koramangala Store',
        medicine_name: 'Pan 40 Gastro-Resistant',
        current_stock: 25,
        daily_sales_rate: 20,
        days_of_stock: 1.3,
      },
    ],
    surplus_data: [
      {
        pharmacy_name: 'MedPlus Koramangala Warehouse',
        batch_number: 'BATCH-002',
        medicine_name: 'Dolo 650mg Paracetamol',
        quantity: 500,
        expiry_date: '2026-11-15',
        days_to_expiry: 65,
        mrp: 32.5,
      },
      {
        pharmacy_name: 'Frank Ross Pharmacy MG Road',
        batch_number: 'BATCH-003',
        medicine_name: 'Pan 40 Gastro-Resistant',
        quantity: 250,
        expiry_date: '2027-04-20',
        days_to_expiry: 88,
        mrp: 54.0,
      },
    ],
  },
};

// Full Day 1-11 realistic historical dataset for demo walkthrough
export const historyMockDB = {
  ...JSON.parse(JSON.stringify(initialMockDB)),
  batches: [
    {
      id: 1,
      batch_number: 'BATCH-001',
      medicine_name: 'Augmentin Duo 625mg',
      brand_name: 'Augmentin Duo',
      generic_name: 'Amoxicillin & Potassium Clavulanate',
      strength: '625mg',
      quantity: 100,
      quantity_to_destroy: 100,
      expiry_date: '2026-08-30',
      expiry_status: 'EXPIRED',
      current_status: 'CLOSED',
      current_location: 'BioClean Incineration Unit #3 (Finalized)',
      reverse_chain_flag: true,
      destruction_status: 'DESTROYED',
      scheduled_status: 'COMPLETED',
      scheduled_date: '2026-09-08',
    },
    ...initialMockDB.batches.slice(1),
  ],
  returnRequests: [
    {
      id: 1001,
      batch_id: 1,
      declared_quantity: 100,
      distributor_id: 3,
      status: 'RECEIVED',
      evidence_id: 'EVD-9421',
      evidence_url: 'https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=500&auto=format&fit=crop&q=60',
    },
  ],
  disputes: [
    {
      id: 2001,
      batch_id: 1,
      declared_qty: 100,
      received_qty: 95,
      status: 'RESOLVED',
      resolution_notes: '5 damaged cartons safely discarded per SOP. Remaining 95 approved for quarantine.',
    },
  ],
  destructionRecords: [
    {
      id: 3001,
      batch_id: 1,
      facility_id: 4,
      quantity_destroyed: 100,
      timestamp: new Date(Date.now() - 3600000 * 24 * 2).toISOString(),
    },
  ],
  certificates: [
    {
      id: 4001,
      certificate_number: 'CERT-DESTROY-994120',
      batch_id: 1,
      facility_id: 4,
      quantity: 100,
      issued_date: '2026-09-09',
      is_verified: true,
    },
  ],
  workflowEvents: [
    {
      id: 108,
      batch_id: 1,
      event_type: 'CERTIFICATE_VERIFIED',
      from_status: 'DESTROYED',
      to_status: 'CLOSED',
      actor_id: 5,
      actor_name: 'CDSCO Regulatory Body',
      actor_role: 'REGULATOR',
      data: { verified_by: 'CDSCO Inspector #78', certificate_number: 'CERT-DESTROY-994120' },
      created_at: new Date(Date.now() - 3600000 * 12).toISOString(),
      time_display: 'Day 11 — 16:30',
    },
    {
      id: 107,
      batch_id: 1,
      event_type: 'DESTROYED',
      from_status: 'DESTRUCTION_SCHEDULED',
      to_status: 'DESTROYED',
      actor_id: 4,
      actor_name: 'BioClean Waste Disposal Facility',
      actor_role: 'FACILITY',
      data: { quantity_destroyed: 100, method: 'High Temperature Thermal Incineration' },
      created_at: new Date(Date.now() - 3600000 * 24 * 2).toISOString(),
      time_display: 'Day 9 — 11:20',
    },
    {
      id: 106,
      batch_id: 1,
      event_type: 'DESTRUCTION_SCHEDULED',
      from_status: 'RECEIVED_BY_MANUFACTURER',
      to_status: 'DESTRUCTION_SCHEDULED',
      actor_id: 2,
      actor_name: 'Sun Pharma Laboratories',
      actor_role: 'MANUFACTURER',
      data: { facility_id: 4, scheduled_date: '2026-09-09' },
      created_at: new Date(Date.now() - 3600000 * 24 * 4).toISOString(),
      time_display: 'Day 7 — 14:00',
    },
    {
      id: 105,
      batch_id: 1,
      event_type: 'DISPUTE_RESOLVED',
      from_status: 'DISPUTED',
      to_status: 'RECEIVED_BY_MANUFACTURER',
      actor_id: 2,
      actor_name: 'Sun Pharma Laboratories',
      actor_role: 'MANUFACTURER',
      data: { notes: '5 damaged cartons safely discarded per SOP.' },
      created_at: new Date(Date.now() - 3600000 * 24 * 5).toISOString(),
      time_display: 'Day 6 — 10:15',
    },
    {
      id: 104,
      batch_id: 1,
      event_type: 'DISCREPANCY_DETECTED',
      from_status: 'PICKUP_CONFIRMED',
      to_status: 'DISPUTED',
      actor_id: 3,
      actor_name: 'BlueDart Logistics',
      actor_role: 'DISTRIBUTOR',
      data: { declared_qty: 100, received_qty: 95 },
      created_at: new Date(Date.now() - 3600000 * 24 * 6).toISOString(),
      time_display: 'Day 5 — 17:45',
    },
    {
      id: 103,
      batch_id: 1,
      event_type: 'PICKUP_CONFIRMED',
      from_status: 'RETURN_REQUESTED',
      to_status: 'PICKUP_CONFIRMED',
      actor_id: 3,
      actor_name: 'BlueDart Logistics',
      actor_role: 'DISTRIBUTOR',
      data: { note: 'Driver scan confirmed at MedPlus Indiranagar.' },
      created_at: new Date(Date.now() - 3600000 * 24 * 8).toISOString(),
      time_display: 'Day 3 — 13:00',
    },
    {
      id: 102,
      batch_id: 1,
      event_type: 'RETURN_REQUESTED',
      from_status: 'EXPIRED',
      to_status: 'RETURN_REQUESTED',
      actor_id: 1,
      actor_name: 'MedPlus Central Indiranagar',
      actor_role: 'PHARMACY',
      data: { declared_quantity: 100, evidence_id: 'EVD-9421' },
      created_at: new Date(Date.now() - 3600000 * 24 * 10).toISOString(),
      time_display: 'Day 1 — 10:30',
    },
    {
      id: 101,
      batch_id: 1,
      event_type: 'EXPIRY_FLAGGED',
      from_status: 'ACTIVE',
      to_status: 'EXPIRED',
      actor_id: 1,
      actor_name: 'MedPlus Central Indiranagar',
      actor_role: 'PHARMACY',
      data: { note: 'Automated shelf inventory expiry scanning threshold reached.' },
      created_at: new Date(Date.now() - 3600000 * 24 * 11).toISOString(),
      time_display: 'Day 1 — 09:15',
    },
  ],
};

export function getMockDB() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (!stored) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(initialMockDB));
    return initialMockDB;
  }
  try {
    return JSON.parse(stored);
  } catch (e) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(initialMockDB));
    return initialMockDB;
  }
}

export function saveMockDB(db) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
}

export function resetMockDB(mode = 'fresh') {
  const dbToSave = mode === 'history' ? JSON.parse(JSON.stringify(historyMockDB)) : JSON.parse(JSON.stringify(initialMockDB));
  localStorage.setItem(STORAGE_KEY, JSON.stringify(dbToSave));
  return dbToSave;
}

// Compute workflow progress matching backend logic
export function computeWorkflowProgress(status) {
  const order = {
    ACTIVE: 0,
    EXPIRED: 1,
    RETURN_REQUESTED: 2,
    PICKUP_CONFIRMED: 3,
    RECEIVED_BY_DISTRIBUTOR: 4,
    DISPUTED: 4,
    RECEIVED_BY_MANUFACTURER: 5,
    DESTRUCTION_SCHEDULED: 6,
    DESTROYED: 7,
    CERTIFICATE_VERIFIED: 8,
    CLOSED: 9,
  };
  const curVal = order[status] ?? 1;

  const thresholds = {
    return: 2,
    pickup: 3,
    distributor_receipt: 4,
    manufacturer_receipt: 5,
    destruction: 7,
    certificate: 8,
  };

  const progress = {};
  for (const [stage, thresh] of Object.entries(thresholds)) {
    if (curVal > thresh) {
      progress[stage] = 'COMPLETED';
    } else if (curVal === thresh) {
      progress[stage] = status === 'DISPUTED' ? 'DISPUTED' : 'CURRENT';
    } else {
      progress[stage] = 'PENDING';
    }
  }
  return progress;
}

// Compute next action label for role
export function getNextActionForRole(role, status) {
  if (role === 'PHARMACY') {
    if (status === 'EXPIRED') return 'Initiate Reverse Chain Return Request for Expired Inventory';
    if (status === 'RETURN_REQUESTED') return 'Awaiting BlueDart Logistics physical pickup confirmation';
    if (status === 'PICKUP_CONFIRMED') return 'Batch in transit — awaiting distributor warehouse receipt & verification';
    if (status === 'RECEIVED_BY_DISTRIBUTOR') return 'Batch received at distributor warehouse — proceeding to manufacturer';
    if (status === 'DISPUTED') return 'Dispute active at distributor — awaiting quantity resolution';
    if (status === 'RECEIVED_BY_MANUFACTURER') return 'Batch safely received at Sun Pharma Laboratories quarantine';
    if (status === 'DESTRUCTION_SCHEDULED') return 'Destruction scheduled at BioClean Biomedical Waste Facility';
    if (status === 'DESTROYED') return 'Destruction completed — awaiting CDSCO regulatory certificate verification';
    if (['CERTIFICATE_VERIFIED', 'CLOSED'].includes(status)) return 'Batch compliance lifecycle CLOSED and cryptographically sealed';
    return 'Monitor batch status';
  }
  if (role === 'DISTRIBUTOR') {
    if (status === 'RETURN_REQUESTED') return 'Confirm physical pickup at MedPlus Central Indiranagar';
    if (status === 'PICKUP_CONFIRMED') return 'Receive and verify inventory count at BlueDart warehouse';
    if (status === 'DISPUTED') return 'Resolve open quantity discrepancy (100 declared vs 95 received)';
    if (status === 'RECEIVED_BY_DISTRIBUTOR') return 'Forward verified batch to Sun Pharma Laboratories';
    return 'Batch successfully transferred to Manufacturer';
  }
  if (role === 'MANUFACTURER') {
    if (status === 'RECEIVED_BY_DISTRIBUTOR') return 'Accept verified return batch from BlueDart Logistics';
    if (status === 'DISPUTED') return 'Review quantity dispute between Pharmacy and Distributor';
    if (status === 'RECEIVED_BY_MANUFACTURER') return 'Schedule batch destruction at BioClean Waste Facility';
    if (status === 'DESTRUCTION_SCHEDULED') return 'Awaiting physical destruction confirmation from BioClean';
    if (status === 'DESTROYED') return 'Destruction recorded — awaiting regulatory certificate verification';
    return 'Batch lifecycle finalized and closed';
  }
  if (role === 'FACILITY') {
    if (status === 'DESTRUCTION_SCHEDULED') return 'Execute thermal destruction and record quantity destroyed';
    if (status === 'DESTROYED') return 'Generate digital Destruction Certificate for regulatory submission';
    if (status === 'CERTIFICATE_VERIFIED' || status === 'CLOSED') return 'Certificate verified by CDSCO — lifecycle complete';
    return 'Awaiting assigned destruction batches';
  }
  if (role === 'REGULATOR') {
    if (status === 'DESTROYED') return 'Inspect and verify digital Destruction Certificate';
    if (status === 'CERTIFICATE_VERIFIED' || status === 'CLOSED') return 'Certificate verified — batch cryptographically sealed';
    if (status === 'DISPUTED') return 'Investigate active supply chain quantity discrepancy';
    return 'Audit network compliance and tamper-evident SHA-256 chain';
  }
  return 'Monitor batch operations';
}
