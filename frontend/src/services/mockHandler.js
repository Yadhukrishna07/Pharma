// Standalone Mock API Handler for PharmMedian Frontend

import {
  getMockDB,
  saveMockDB,
  resetMockDB,
  computeWorkflowProgress,
  getNextActionForRole,
} from './mockData';

function sha256Hex(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash |= 0;
  }
  const hex = Math.abs(hash).toString(16).padStart(16, '0');
  return (hex + hex + hex + hex).slice(0, 64);
}

export function handleMockRequest(url, method = 'GET', data = null) {
  const db = getMockDB();
  const lowerUrl = url.toLowerCase();
  const upperMethod = method.toUpperCase();

  // Helper to format response object like Axios ({ data: ... , status: 200, statusText: 'OK' })
  const mockResp = (payload, status = 200) => ({ data: payload, status, statusText: 'OK' });

  // ──────────────────────────────────────────────
  // 1. Auth API
  // ──────────────────────────────────────────────
  if (lowerUrl.includes('/auth/me')) {
    return mockResp(db.currentUser);
  }

  if (lowerUrl.includes('/auth/switch-role')) {
    const role = (data && data.role) || 'PHARMACY';
    const user = db.users[role] || db.users.PHARMACY;
    db.currentUser = user;
    saveMockDB(db);
    return mockResp({
      access_token: `mock-jwt-token-${role.toLowerCase()}`,
      token_type: 'bearer',
      user: user,
    });
  }

  if (lowerUrl.includes('/auth/login')) {
    const role = (data && data.username && data.username.includes('distributor'))
      ? 'DISTRIBUTOR'
      : (data && data.username && data.username.includes('manufacturer'))
      ? 'MANUFACTURER'
      : (data && data.username && data.username.includes('facility'))
      ? 'FACILITY'
      : (data && data.username && data.username.includes('regulator'))
      ? 'REGULATOR'
      : 'PHARMACY';
    const user = db.users[role] || db.users.PHARMACY;
    db.currentUser = user;
    saveMockDB(db);
    return mockResp({
      access_token: `mock-jwt-token-${role.toLowerCase()}`,
      token_type: 'bearer',
      user: user,
    });
  }

  if (lowerUrl.includes('/auth/register')) {
    const role = (data && data.role) || 'PHARMACY';
    const user = {
      id: Date.now(),
      username: data?.username || 'new_user',
      email: data?.email || 'user@pharma.com',
      role: role,
      organization_name: data?.organization_name || 'Registered Organization',
    };
    db.users[role] = user;
    db.currentUser = user;
    saveMockDB(db);
    return mockResp({
      access_token: `mock-jwt-token-${role.toLowerCase()}`,
      token_type: 'bearer',
      user: user,
    });
  }

  if (lowerUrl.includes('/auth/notifications/count')) {
    const count = db.notifications.filter((n) => !n.read_status).length;
    return mockResp({ count });
  }

  if (lowerUrl.includes('/auth/notifications')) {
    if (lowerUrl.includes('/read')) {
      const parts = lowerUrl.split('/');
      const id = parseInt(parts[parts.indexOf('notifications') + 1], 10);
      db.notifications = db.notifications.map((n) =>
        n.id === id ? { ...n, read_status: true } : n
      );
      saveMockDB(db);
      return mockResp({ status: 'ok' });
    }
    return mockResp(db.notifications);
  }

  // ──────────────────────────────────────────────
  // 2. Dashboards API
  // ──────────────────────────────────────────────
  if (lowerUrl.includes('/dashboard/reset')) {
    const mode = data?.mode || 'fresh';
    const newDb = resetMockDB(mode);
    return mockResp({ message: `Dashboard reset to ${mode} mode`, mode });
  }

  if (lowerUrl.includes('/dashboard/stats')) {
    return mockResp({
      total_batches: db.batches.length,
      active_returns: db.returnRequests.length,
      resolved_disputes: db.disputes.filter((d) => d.status === 'RESOLVED').length,
      completed_destructions: db.destructionRecords.length,
      verified_certificates: db.certificates.filter((c) => c.is_verified).length,
      critical_alerts: db.alerts.filter((a) => a.severity === 'CRITICAL').length,
    });
  }

  if (lowerUrl.includes('/dashboard/pharmacy')) {
    const batch = db.batches[0];
    const ret = db.returnRequests.find((r) => r.batch_id === batch.id);
    return mockResp({
      role: 'PHARMACY',
      organization_name: db.currentUser.organization_name || 'MedPlus Central Indiranagar',
      batch: batch,
      return_request: ret || null,
      return_status: ret ? ret.status : 'NOT_INITIATED',
      progress: computeWorkflowProgress(batch.current_status),
      next_action: getNextActionForRole('PHARMACY', batch.current_status),
      recent_activity: db.workflowEvents.filter((e) => e.batch_id === batch.id),
      moderator_insight: db.moderatorEvents.find((m) => m.batch_id === batch.id) || null,
      alerts: db.alerts,
    });
  }

  if (lowerUrl.includes('/dashboard/distributor')) {
    const batch = db.batches[0];
    const ret = db.returnRequests.find((r) => r.batch_id === batch.id);
    const dispute = db.disputes.find((d) => d.batch_id === batch.id);
    const expectedQty = ret ? ret.declared_quantity : (batch ? batch.quantity : 100);
    const receivedQty = dispute ? dispute.received_qty : (['RECEIVED_BY_DISTRIBUTOR', 'RECEIVED_BY_MANUFACTURER', 'DESTRUCTION_SCHEDULED', 'DESTROYED', 'CERTIFICATE_VERIFIED', 'CLOSED'].includes(batch.current_status) ? expectedQty : null);

    return mockResp({
      role: 'DISTRIBUTOR',
      organization_name: 'BlueDart Pharma Logistics',
      batch: batch,
      incoming_return: ret || null,
      dispute: dispute || null,
      expected_quantity: expectedQty,
      received_quantity: receivedQty,
      pickup_state: ['PICKUP_CONFIRMED', 'RECEIVED_BY_DISTRIBUTOR', 'DISPUTED', 'RECEIVED_BY_MANUFACTURER', 'DESTRUCTION_SCHEDULED', 'DESTROYED', 'CERTIFICATE_VERIFIED', 'CLOSED'].includes(batch.current_status) ? 'CONFIRMED' : 'PENDING',
      receipt_state: ['RECEIVED_BY_DISTRIBUTOR', 'RECEIVED_BY_MANUFACTURER', 'DESTRUCTION_SCHEDULED', 'DESTROYED', 'CERTIFICATE_VERIFIED', 'CLOSED'].includes(batch.current_status) ? 'RECEIVED' : (batch.current_status === 'DISPUTED' ? 'DISPUTED' : 'AWAITING'),
      progress: computeWorkflowProgress(batch.current_status),
      next_action: getNextActionForRole('DISTRIBUTOR', batch.current_status),
      recent_activity: db.workflowEvents.filter((e) => e.batch_id === batch.id),
      moderator_insight: db.moderatorEvents.find((m) => m.batch_id === batch.id) || null,
      alerts: db.alerts,
    });
  }

  if (lowerUrl.includes('/dashboard/manufacturer')) {
    const batch = db.batches[0];
    const dispute = db.disputes.find((d) => d.batch_id === batch.id);
    return mockResp({
      role: 'MANUFACTURER',
      organization_name: 'Sun Pharma Laboratories',
      batch: batch,
      dispute: dispute || null,
      facility_id: 4,
      facility_name: 'BioClean Biomedical Waste Facility',
      manufacturer_receipt_state: ['RECEIVED_BY_MANUFACTURER', 'DESTRUCTION_SCHEDULED', 'DESTROYED', 'CERTIFICATE_VERIFIED', 'CLOSED'].includes(batch.current_status) ? 'CONFIRMED' : 'PENDING',
      destruction_scheduling_state: ['DESTRUCTION_SCHEDULED', 'DESTROYED', 'CERTIFICATE_VERIFIED', 'CLOSED'].includes(batch.current_status) ? 'SCHEDULED' : 'PENDING',
      progress: computeWorkflowProgress(batch.current_status),
      next_action: getNextActionForRole('MANUFACTURER', batch.current_status),
      recent_activity: db.workflowEvents.filter((e) => e.batch_id === batch.id),
      moderator_insight: db.moderatorEvents.find((m) => m.batch_id === batch.id) || null,
      alerts: db.alerts,
    });
  }

  if (lowerUrl.includes('/dashboard/facility')) {
    const batch = db.batches[0];
    const rec = db.destructionRecords.find((d) => d.batch_id === batch.id);
    const cert = db.certificates.find((c) => c.batch_id === batch.id);
    
    // Ensure facility-required properties exist on batch object
    const facilityBatch = {
      ...batch,
      quantity_to_destroy: batch.quantity_to_destroy || batch.quantity || 100,
      scheduled_status: ['DESTRUCTION_SCHEDULED', 'DESTROYED', 'CERTIFICATE_VERIFIED', 'CLOSED'].includes(batch.current_status) ? 'SCHEDULED' : 'PENDING',
      scheduled_date: batch.scheduled_date || (['DESTRUCTION_SCHEDULED', 'DESTROYED', 'CERTIFICATE_VERIFIED', 'CLOSED'].includes(batch.current_status) ? 'Scheduled for today' : 'Pending'),
      destruction_status: batch.destruction_status || (['DESTROYED', 'CERTIFICATE_VERIFIED', 'CLOSED'].includes(batch.current_status) ? 'DESTROYED' : 'PENDING'),
    };

    const certStatus = cert?.is_verified ? 'CERTIFICATE_VERIFIED_CLOSED' : (cert ? 'ISSUED_AWAITING_VERIFICATION' : 'PENDING');

    return mockResp({
      role: 'FACILITY',
      organization_name: 'BioClean Waste Disposal Facility',
      batch: facilityBatch,
      destruction_record: rec || null,
      certificate: cert || null,
      certificate_status: certStatus,
      progress: computeWorkflowProgress(batch.current_status),
      next_action: getNextActionForRole('FACILITY', batch.current_status),
      recent_activity: db.workflowEvents.filter((e) => e.batch_id === batch.id),
      moderator_insight: db.moderatorEvents.find((m) => m.batch_id === batch.id) || null,
      alerts: db.alerts,
    });
  }

  if (lowerUrl.includes('/dashboard/regulator')) {
    const batch = db.batches[0];
    const cert = db.certificates.find((c) => c.batch_id === batch.id);
    const summaryCards = {
      active_returns: db.returnRequests.filter((r) => r.status !== 'REJECTED' && r.status !== 'CLOSED').length || 1,
      pending_destruction: db.batches.filter((b) => b.current_status === 'DESTRUCTION_SCHEDULED').length,
      verified_destruction: db.certificates.filter((c) => c.is_verified).length,
      critical_fraud_alerts: db.alerts.filter((a) => a.severity === 'CRITICAL').length,
    };

    const auditVerification = {
      is_valid: true,
      total_records: db.workflowEvents.length + 5,
      verified_records: db.workflowEvents.length + 5,
      message: 'All audit log records verified. Cryptographic SHA-256 chain intact.',
    };

    return mockResp({
      role: 'REGULATOR',
      organization_name: 'CDSCO Regulatory Body',
      batch: batch,
      certificate: cert || null,
      certificates: db.certificates,
      summary_cards: summaryCards,
      timeline: db.workflowEvents.filter((e) => e.batch_id === batch.id),
      progress: computeWorkflowProgress(batch.current_status),
      next_action: getNextActionForRole('REGULATOR', batch.current_status),
      recent_activity: db.workflowEvents.filter((e) => e.batch_id === batch.id),
      moderator_insight: db.moderatorEvents.find((m) => m.batch_id === batch.id) || null,
      alerts: db.alerts,
      audit_verification: auditVerification,
      audit_integrity: auditVerification,
    });
  }

  // ──────────────────────────────────────────────
  // 3. Batches API
  // ──────────────────────────────────────────────
  if (lowerUrl.includes('/batches/scan')) {
    const batchNum = data?.batch_number || 'BATCH-001';
    let batch = db.batches.find((b) => b.batch_number === batchNum);
    if (!batch) {
      batch = db.batches[0];
    }

    if (['DESTROYED', 'CERTIFICATE_VERIFIED', 'CLOSED'].includes(batch.current_status)) {
      // Re-entry fraud detected!
      const alertMsg = `CRITICAL: Re-entry fraud detected for batch ${batch.batch_number}. Batch status is ${batch.current_status} but was scanned at ${data?.location || 'unknown'}.`;
      
      db.alerts.unshift({
        id: Date.now(),
        batch_id: batch.id,
        severity: 'CRITICAL',
        title: 'REENTRY_FRAUD_EVENT',
        description: alertMsg,
        is_acknowledged: false,
        created_at: new Date().toISOString(),
        time_display: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      });

      db.moderatorEvents.unshift({
        id: Date.now() + 1,
        workflow_event_id: Date.now() + 2,
        batch_id: batch.id,
        risk_level: 'CRITICAL',
        analysis: `Re-entry fraud alert! Scanned destroyed batch ${batch.batch_number} at ${data?.location || 'unauthorized location'}. State preserved in ${batch.current_status}.`,
        recommended_action: 'Quarantine scanned items immediately and alert regional CDSCO regulatory inspectors.',
        message: 'CRITICAL ALERT: Unauthorized batch scan detected for destroyed drug inventory.',
      });

      db.notifications.unshift({
        id: Date.now() + 3,
        user_id: db.currentUser.id,
        title: 'CRITICAL: Re-Entry Fraud Alert',
        message: `Unauthorized scan of destroyed batch ${batch.batch_number} at ${data?.location || 'retail pharmacy'}. CDSCO alerted.`,
        read_status: false,
        created_at: new Date().toISOString(),
      });

      saveMockDB(db);

      return mockResp({
        batch: batch,
        fraud_detected: true,
        alert: alertMsg,
        message: 'Re-entry fraud detected. Authorities have been notified.',
      });
    }

    return mockResp({
      batch: batch,
      fraud_detected: false,
      alert: null,
      message: `Batch ${batch.batch_number} scanned successfully. Status: ${batch.current_status}.`,
    });
  }

  if (lowerUrl.includes('/batches') && upperMethod === 'GET') {
    if (lowerUrl.includes('/timeline')) {
      const parts = lowerUrl.split('/');
      const batchId = parseInt(parts[parts.indexOf('batches') + 1], 10) || 1;
      const events = db.workflowEvents.filter((e) => e.batch_id === batchId);
      return mockResp(events);
    }
    if (lowerUrl.includes('/moderator-events')) {
      const parts = lowerUrl.split('/');
      const batchId = parseInt(parts[parts.indexOf('batches') + 1], 10) || 1;
      const events = db.moderatorEvents.filter((e) => e.batch_id === batchId);
      return mockResp(events);
    }
    const parts = lowerUrl.split('/');
    const lastPart = parts[parts.length - 1] || parts[parts.length - 2];
    const batchId = parseInt(lastPart, 10);
    if (!isNaN(batchId)) {
      const batch = db.batches.find((b) => b.id === batchId) || db.batches[0];
      return mockResp(batch);
    }
    return mockResp(db.batches);
  }

  // ──────────────────────────────────────────────
  // 4. Return Requests API
  // ──────────────────────────────────────────────
  if (lowerUrl.includes('/returns')) {
    if (upperMethod === 'POST' && lowerUrl.includes('/pickup')) {
      const batch = db.batches[0];
      batch.current_status = 'PICKUP_CONFIRMED';
      batch.current_location = 'BlueDart Logistics Transit Van #12';

      if (db.returnRequests[0]) {
        db.returnRequests[0].status = 'PICKED_UP';
      }

      db.workflowEvents.unshift({
        id: Date.now(),
        batch_id: batch.id,
        event_type: 'PICKUP_CONFIRMED',
        from_status: 'RETURN_REQUESTED',
        to_status: 'PICKUP_CONFIRMED',
        actor_id: 3,
        actor_name: 'BlueDart Logistics',
        actor_role: 'DISTRIBUTOR',
        data: { note: 'Driver scan confirmed at MedPlus Indiranagar.' },
        created_at: new Date().toISOString(),
        time_display: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      });

      saveMockDB(db);
      return mockResp({ status: 'PICKUP_CONFIRMED', batch });
    }

    if (upperMethod === 'POST' && lowerUrl.includes('/receive')) {
      const batch = db.batches[0];
      const recQty = data?.received_quantity || 100;
      const decQty = db.returnRequests[0]?.declared_quantity || 100;

      if (recQty !== decQty) {
        batch.current_status = 'DISPUTED';
        batch.current_location = 'BlueDart Regional Warehouse — Under Dispute';

        const newDispute = {
          id: Date.now(),
          batch_id: batch.id,
          declared_qty: decQty,
          received_qty: recQty,
          status: 'OPEN',
          resolution_notes: null,
        };
        db.disputes.unshift(newDispute);

        if (db.returnRequests[0]) {
          db.returnRequests[0].status = 'DISPUTED';
        }

        db.alerts.unshift({
          id: Date.now() + 1,
          batch_id: batch.id,
          severity: 'HIGH',
          title: 'QUANTITY_DISCREPANCY_DETECTED',
          description: `Declared ${decQty} units vs Received ${recQty} units. Discrepancy of ${decQty - recQty} units.`,
          is_acknowledged: false,
          created_at: new Date().toISOString(),
          time_display: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        });

        db.workflowEvents.unshift({
          id: Date.now() + 2,
          batch_id: batch.id,
          event_type: 'DISCREPANCY_DETECTED',
          from_status: 'PICKUP_CONFIRMED',
          to_status: 'DISPUTED',
          actor_id: 3,
          actor_name: 'BlueDart Logistics',
          actor_role: 'DISTRIBUTOR',
          data: { declared_qty: decQty, received_qty: recQty },
          created_at: new Date().toISOString(),
          time_display: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        });

        saveMockDB(db);
        return mockResp({
          status: 'disputed',
          batch_status: 'DISPUTED',
          dispute_id: newDispute.id,
          message: `Discrepancy detected: declared ${decQty}, received ${recQty}`,
          batch,
        });
      } else {
        batch.current_status = 'RECEIVED_BY_DISTRIBUTOR';
        batch.current_location = 'BlueDart Regional Warehouse Section C';

        if (db.returnRequests[0]) {
          db.returnRequests[0].status = 'RECEIVED';
        }

        db.workflowEvents.unshift({
          id: Date.now(),
          batch_id: batch.id,
          event_type: 'RECEIVED_BY_DISTRIBUTOR',
          from_status: 'PICKUP_CONFIRMED',
          to_status: 'RECEIVED_BY_DISTRIBUTOR',
          actor_id: 3,
          actor_name: 'BlueDart Logistics',
          actor_role: 'DISTRIBUTOR',
          data: { received_quantity: recQty },
          created_at: new Date().toISOString(),
          time_display: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        });

        saveMockDB(db);
        return mockResp({
          status: 'ok',
          batch_status: 'RECEIVED_BY_DISTRIBUTOR',
          message: 'Return quantity verified and accepted.',
          batch,
        });
      }
    }

    if (upperMethod === 'POST') {
      const batch = db.batches[0];
      batch.current_status = 'RETURN_REQUESTED';
      batch.reverse_chain_flag = true;

      const newReturn = {
        id: Date.now(),
        batch_id: batch.id,
        declared_quantity: data?.declared_quantity || 100,
        distributor_id: data?.distributor_id || 3,
        status: 'PENDING',
        evidence_id: data?.evidence_id || 'EVD-9821',
        evidence_url: data?.evidence_url || 'https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=500&auto=format&fit=crop&q=60',
      };

      db.returnRequests.unshift(newReturn);

      db.workflowEvents.unshift({
        id: Date.now() + 1,
        batch_id: batch.id,
        event_type: 'RETURN_REQUESTED',
        from_status: 'EXPIRED',
        to_status: 'RETURN_REQUESTED',
        actor_id: 1,
        actor_name: 'MedPlus Central Indiranagar',
        actor_role: 'PHARMACY',
        data: { declared_quantity: newReturn.declared_quantity, evidence_id: newReturn.evidence_id },
        created_at: new Date().toISOString(),
        time_display: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      });

      saveMockDB(db);
      return mockResp(newReturn);
    }

    return mockResp(db.returnRequests);
  }

  // ──────────────────────────────────────────────
  // 5. Disputes API
  // ──────────────────────────────────────────────
  if (lowerUrl.includes('/disputes')) {
    if (upperMethod === 'POST' && lowerUrl.includes('/resolve')) {
      const batch = db.batches[0];
      batch.current_status = 'RECEIVED_BY_MANUFACTURER';
      batch.current_location = 'Sun Pharma Quarantine Vault A1';

      if (db.disputes[0]) {
        db.disputes[0].status = 'RESOLVED';
        db.disputes[0].resolution_notes = data?.resolution_notes || 'Discrepancy resolved via physical inventory recount.';
      }

      db.workflowEvents.unshift({
        id: Date.now(),
        batch_id: batch.id,
        event_type: 'DISPUTE_RESOLVED',
        from_status: 'DISPUTED',
        to_status: 'RECEIVED_BY_MANUFACTURER',
        actor_id: 2,
        actor_name: 'Sun Pharma Laboratories',
        actor_role: 'MANUFACTURER',
        data: { notes: data?.resolution_notes },
        created_at: new Date().toISOString(),
        time_display: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      });

      saveMockDB(db);
      return mockResp({ status: 'RESOLVED', batch });
    }
    return mockResp(db.disputes);
  }

  // ──────────────────────────────────────────────
  // 6. Destruction & Handoff API
  // ──────────────────────────────────────────────
  if (lowerUrl.includes('/destruction')) {
    if (lowerUrl.includes('/handoff')) {
      const batch = db.batches[0];
      batch.current_status = 'RECEIVED_BY_MANUFACTURER';
      batch.current_location = 'Sun Pharma Quarantine Vault A1';

      db.workflowEvents.unshift({
        id: Date.now(),
        batch_id: batch.id,
        event_type: 'MANUFACTURER_HANDOFF',
        from_status: 'RECEIVED_BY_DISTRIBUTOR',
        to_status: 'RECEIVED_BY_MANUFACTURER',
        actor_id: 2,
        actor_name: 'Sun Pharma Laboratories',
        actor_role: 'MANUFACTURER',
        data: { location: batch.current_location },
        created_at: new Date().toISOString(),
        time_display: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      });

      saveMockDB(db);
      return mockResp({ status: 'RECEIVED_BY_MANUFACTURER', batch });
    }

    if (lowerUrl.includes('/schedule')) {
      const batch = db.batches[0];
      batch.current_status = 'DESTRUCTION_SCHEDULED';
      batch.current_location = 'BioClean Disposal Storage Facility';
      batch.scheduled_status = 'SCHEDULED';
      batch.scheduled_date = 'Today';

      db.workflowEvents.unshift({
        id: Date.now(),
        batch_id: batch.id,
        event_type: 'DESTRUCTION_SCHEDULED',
        from_status: 'RECEIVED_BY_MANUFACTURER',
        to_status: 'DESTRUCTION_SCHEDULED',
        actor_id: 2,
        actor_name: 'Sun Pharma Laboratories',
        actor_role: 'MANUFACTURER',
        data: { facility_id: data?.facility_id || 4 },
        created_at: new Date().toISOString(),
        time_display: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      });

      saveMockDB(db);
      return mockResp({ status: 'DESTRUCTION_SCHEDULED', batch });
    }

    if (lowerUrl.includes('/record')) {
      const batch = db.batches[0];
      const qtyDestroyed = data?.quantity_destroyed || batch.quantity || 100;
      batch.current_status = 'DESTROYED';
      batch.destruction_status = 'DESTROYED';
      batch.quantity_to_destroy = qtyDestroyed;
      batch.current_location = 'BioClean Incineration Unit #3';

      const newRec = {
        id: Date.now(),
        batch_id: batch.id,
        facility_id: 4,
        quantity_destroyed: qtyDestroyed,
        timestamp: new Date().toISOString(),
      };
      db.destructionRecords.unshift(newRec);

      db.workflowEvents.unshift({
        id: Date.now() + 1,
        batch_id: batch.id,
        event_type: 'DESTROYED',
        from_status: 'DESTRUCTION_SCHEDULED',
        to_status: 'DESTROYED',
        actor_id: 4,
        actor_name: 'BioClean Waste Disposal Facility',
        actor_role: 'FACILITY',
        data: { quantity_destroyed: qtyDestroyed },
        created_at: new Date().toISOString(),
        time_display: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      });

      saveMockDB(db);
      return mockResp({ status: 'DESTROYED', batch, destruction_record: newRec });
    }
  }

  // ──────────────────────────────────────────────
  // 7. Certificates API
  // ──────────────────────────────────────────────
  if (lowerUrl.includes('/certificates')) {
    if (upperMethod === 'POST' && lowerUrl.includes('/verify')) {
      const batch = db.batches[0];
      batch.current_status = 'CLOSED';

      const parts = lowerUrl.split('/');
      const certId = parseInt(parts[parts.indexOf('certificates') + 1], 10);
      const cert = db.certificates.find((c) => c.id === certId) || db.certificates[0];
      if (cert) {
        cert.is_verified = true;
      }

      db.workflowEvents.unshift({
        id: Date.now(),
        batch_id: batch.id,
        event_type: 'CERTIFICATE_VERIFIED',
        from_status: 'DESTROYED',
        to_status: 'CLOSED',
        actor_id: 5,
        actor_name: 'CDSCO Regulatory Body',
        actor_role: 'REGULATOR',
        data: { verified_by: 'CDSCO Inspector #78' },
        created_at: new Date().toISOString(),
        time_display: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      });

      saveMockDB(db);
      return mockResp({ status: 'CLOSED', is_verified: true, batch, certificate: cert });
    }

    if (upperMethod === 'POST') {
      const batch = db.batches[0];
      batch.current_status = 'CERTIFICATE_VERIFIED';

      const newCert = {
        id: Date.now(),
        certificate_number: data?.certificate_number || `CERT-DESTROY-${Date.now().toString().slice(-6)}`,
        batch_id: batch.id,
        facility_id: 4,
        quantity: data?.quantity || batch.quantity,
        issued_date: new Date().toISOString().split('T')[0],
        is_verified: false,
      };

      db.certificates.unshift(newCert);
      saveMockDB(db);
      return mockResp(newCert);
    }

    const parts = lowerUrl.split('/');
    const lastPart = parts[parts.length - 1] || parts[parts.length - 2];
    const certId = parseInt(lastPart, 10);
    if (!isNaN(certId)) {
      const cert = db.certificates.find((c) => c.id === certId) || db.certificates[0];
      return mockResp(cert);
    }

    return mockResp(db.certificates);
  }

  // ──────────────────────────────────────────────
  // 8. Audit & Alerts API
  // ──────────────────────────────────────────────
  if (lowerUrl.includes('/audit/verify')) {
    return mockResp({
      is_valid: true,
      total_records: db.workflowEvents.length + 5,
      verified_records: db.workflowEvents.length + 5,
      message: `All ${db.workflowEvents.length + 5} audit records verified. Cryptographic SHA-256 chain is intact.`,
    });
  }

  if (lowerUrl.includes('/audit')) {
    const logs = db.workflowEvents.map((e, idx) => ({
      id: e.id,
      batch_id: e.batch_id,
      actor_id: e.actor_id,
      actor_name: e.actor_name,
      actor_role: e.actor_role,
      action: e.event_type,
      timestamp: e.created_at,
      previous_hash: idx === 0 ? '0'.repeat(64) : sha256Hex(`prev-${idx}`),
      current_hash: sha256Hex(`curr-${idx}-${e.event_type}`),
    }));
    return mockResp(logs);
  }

  if (lowerUrl.includes('/alerts')) {
    if (lowerUrl.includes('/acknowledge')) {
      const parts = lowerUrl.split('/');
      const alertId = parseInt(parts[parts.indexOf('alerts') + 1], 10);
      db.alerts = db.alerts.map((a) =>
        a.id === alertId ? { ...a, is_acknowledged: true } : a
      );
      saveMockDB(db);
      return mockResp({ status: 'ok', acknowledged: true });
    }

    if (lowerUrl.includes('/critical')) {
      return mockResp(db.alerts.filter((a) => a.severity === 'CRITICAL'));
    }
    return mockResp(db.alerts);
  }

  // ──────────────────────────────────────────────
  // 9. Reallocation API
  // ──────────────────────────────────────────────
  if (lowerUrl.includes('/reallocation')) {
    if (lowerUrl.includes('/raw-data')) {
      return mockResp(db.reallocationRawData);
    }
    if (lowerUrl.includes('/recommendations')) {
      return mockResp({
        summary: 'Smart Supply-Demand Engine analyzed regional network pharmacies. Identified inter-pharmacy inventory rebalancing to prevent near-expiry waste.',
        recommendations: db.reallocationRecommendations,
      });
    }
    return mockResp({
      summary: 'Smart Supply-Demand Engine analyzed regional network pharmacies. Identified inter-pharmacy inventory rebalancing to prevent near-expiry waste.',
      recommendations: db.reallocationRecommendations,
      raw_data: db.reallocationRawData,
    });
  }

  // ──────────────────────────────────────────────
  // 10. Evidence Upload API
  // ──────────────────────────────────────────────
  if (lowerUrl.includes('/evidence/upload')) {
    const evId = `EVD-${Math.floor(1000 + Math.random() * 9000)}`;
    const sampleImageUrl = 'https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=500&auto=format&fit=crop&q=60';
    return mockResp({
      evidence_id: evId,
      filename: 'package_seal_verification.jpg',
      url: sampleImageUrl,
      file_url: sampleImageUrl,
      timestamp: new Date().toISOString(),
      gps: { latitude: 12.9716, longitude: 77.5946, location_name: 'Indiranagar, Bengaluru' },
    });
  }

  // ──────────────────────────────────────────────
  // 11. AI Chatbot API
  // ──────────────────────────────────────────────
  if (lowerUrl.includes('/chatbot/message')) {
    const userMsg = (data?.message || '').toLowerCase();
    let reply = 'I am the PharmMedian Assistant. I am monitoring batch compliance, reverse chain returns, and cryptographic audit records across all 5 network personas.';

    if (userMsg.includes('batch') || userMsg.includes('status') || userMsg.includes('augmentin')) {
      const b = db.batches[0];
      reply = `Batch **${b.batch_number}** (${b.medicine_name}) is currently in status **${b.current_status}** at location: *${b.current_location}*. Expiry date: ${b.expiry_date}.`;
    } else if (userMsg.includes('return') || userMsg.includes('expired')) {
      reply = 'Expired batches undergo closed-loop reverse chain returns: PHARMACY (Return Requested) → DISTRIBUTOR (Pickup & Receipt) → MANUFACTURER (Quarantine) → FACILITY (Thermal Destruction) → REGULATOR (Certificate Verification).';
    } else if (userMsg.includes('fraud') || userMsg.includes('counterfeit') || userMsg.includes('scan')) {
      reply = 'PharmMedian enforces state invariance on scans. Scanning a DESTROYED or CLOSED batch raises a CRITICAL Re-Entry Fraud alert to regulators without resetting the batch status back to ACTIVE.';
    } else if (userMsg.includes('audit') || userMsg.includes('hash') || userMsg.includes('sha')) {
      reply = 'All workflow state transitions generate a tamper-evident SHA-256 hash entry where Current_Hash = SHA256(Previous_Hash + EventData + Timestamp + ActorID). Verification confirms zero database tampering.';
    } else if (userMsg.includes('reallocat') || userMsg.includes('redistribut')) {
      reply = 'Our Smart Reallocation Engine matches pharmacies facing stock-outs with nearby near-expiry surplus stock to eliminate waste before drugs ever expire.';
    }

    return mockResp({ reply });
  }

  // Default fallback
  return mockResp({ status: 'ok' });
}
