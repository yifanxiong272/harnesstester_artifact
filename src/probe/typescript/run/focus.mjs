export function focusTargetPacket(packet, sampleIndex, lane = "hard_core") {
  const units = (packet.target_units || []).filter(
    (unit) => unit && typeof unit === "object",
  );
  if (units.length === 0) {
    return packet;
  }
  const focus = units[(Math.max(1, sampleIndex) - 1) % units.length];
  return {
    ...packet,
    lane,
    all_target_units: units,
    target_units: [focus],
    focus_target_unit_id: String(focus.unit_id || ""),
    focus_sample_index: sampleIndex,
    focus_total_target_units: units.length,
    focus_target_unit: unitIdentity(focus),
    source_file_index: focusSourceFileIndex(
      packet.source_file_index || [],
      focus,
    ),
    existing_tests: focusExistingTests(
      packet.existing_tests || [],
      focus,
      units.length,
    ),
    module_contracts: focusFileRecords(packet.module_contracts || [], focus),
    module_imports: focusFileRecords(packet.module_imports || [], focus),
    public_target_routes: focusPublicTargetRoutes(
      packet.public_target_routes,
      focus,
    ),
    retrieved_context: focusRetrievedContext(packet.retrieved_context, focus),
  };
}

export function softTargetPacket(packet, sampleIndex) {
  return {
    ...packet,
    lane: "soft_extension",
    whole_target_pass: true,
    soft_sample_index: sampleIndex,
  };
}

export function unitIdentity(unit) {
  return {
    unit_id: String(unit.unit_id || ""),
    filepath: String(unit.filepath || ""),
    qualname: String(unit.qualname || ""),
    kind: String(unit.kind || ""),
  };
}

function focusSourceFileIndex(entries, focus) {
  return entries.filter((item) => item?.path === focus.filepath);
}

function focusExistingTests(tests, focus, totalUnits) {
  if (totalUnits <= 1) {
    return tests;
  }
  const unitId = String(focus.unit_id || "");
  const filepath = String(focus.filepath || "");
  return tests.filter(
    (item) =>
      (item.target_unit_ids || []).includes(unitId) ||
      (item.target_filepaths || []).includes(filepath),
  );
}

function focusFileRecords(records, focus) {
  const filepath = String(focus.filepath || "");
  return records.filter((item) => item?.filepath === filepath);
}

function focusPublicTargetRoutes(routes, focus) {
  if (!routes || typeof routes !== "object") {
    return {};
  }
  const targets = (routes.targets || []).filter(
    (item) => item?.target_unit_id === focus.unit_id,
  );
  return {
    source:
      routes.source || "target-revision TypeScript AST public reachability",
    available: Boolean(routes.available),
    targets,
    unreachable_target_unit_ids: targets
      .filter((item) => item.accessibility === "private_unreachable")
      .map((item) => item.target_unit_id),
  };
}

function focusRetrievedContext(context, focus) {
  if (!context || typeof context !== "object") {
    return {};
  }
  const requests = (context.requests || []).filter(
    (item) => item?.status === "found" && item.filepath === focus.filepath,
  );
  return requests.length ? { ...context, requests } : {};
}
