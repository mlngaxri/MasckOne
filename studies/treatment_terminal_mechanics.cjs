"use strict";

/*
 * Source-bound diagnostic for the intended V7 terminal contact and leaf models.
 * Run from the repository root: node studies/treatment_terminal_mechanics.cjs
 * No CAD, skin-contact settings, actuator firmware or physical qualification.
 *
 * The contact certificate concerns ONLY four intended frictionless, planar
 * full-seat terminal patches. It is not an exact B-rep contact solution.
 * Other rail, detent, key, friction or deformed contacts can change equilibrium.
 * Such contacts must be identified and modeled before claiming rigid-datum load
 * transfer. A nonpositive certificate is inconclusive, never a closure PASS.
 */

const SOURCE_HEAD = "cd8ca3e1764ec1a5144289a613c32d4ebcd2da46";
const BINDINGS = {
  "src/masck_one/structural_frame_actuator_mates.py": "3cedc1a0032b418d9e02592bb4996e29dc9632b7",
  "src/masck_one/treatment_terminal_datum_preload_v2.py": "a51800976ac5b31f29cfeac286a5425cb71bcb60",
  "src/masck_one/treatment_mounted_four_zone_v7.py": "26b6ab2a8e26e17a721c730e358d51c70edf3eee",
  "studies/treatment_buttery_terminal_profile_v2.py": "2df3ff24e7dea813e36d9b738bbe77add2eecb44"
};

function positive(value, label, allowZero = false) {
  if (!Number.isFinite(value) || (allowZero ? value < 0 : value <= 0))
    throw new Error("invalid " + label);
  return value;
}

function numericConstant(content, name) {
  const matches = Array.from(content.matchAll(
    new RegExp("^" + name + "\\s*=\\s*([^\\n#]+)", "gm")
  ));
  if (matches.length !== 1) throw new Error("ambiguous or missing " + name);
  const value = Number(matches[0][1].trim());
  if (!Number.isFinite(value)) throw new Error("nonfinite/nonliteral " + name);
  return value;
}

function verifyBindings(files) {
  for (const [path, expected] of Object.entries(BINDINGS)) {
    const file = files[path];
    if (!file || file.git_blob_sha !== expected || typeof file.content !== "string")
      throw new Error("changed or missing consumed source: " + path);
  }
}

/*
 * Inboard bottom Z master occupies x in [-W/2, -W/2+a].
 * Outboard top Z preload occupies x in [W/2-b, W/2].
 * Their force-balanced resultants produce My >= Pz*(W-a-b).
 * Equal-and-opposite X normals can supply at most Px*H opposing My,
 * since their actual shoulder contact z lies within [-H/2,H/2].
 * Consequently My_residual >= Pz*(W-a-b) - Px*H.
 * Reflection reverses torque sign, not this magnitude certificate.
 */
function contactCertificate({width, thickness, masterSpan, preloadSpan, px, pz}) {
  for (const [label, value] of Object.entries(
    {width, thickness, masterSpan, preloadSpan, px, pz}
  )) positive(value, label);
  if (masterSpan > width || preloadSpan > width)
    throw new Error("patch exceeds shoulder width");
  const separation = Math.max(0, width - masterSpan - preloadSpan);
  const zMoment = pz * separation;
  const xMoment = px * thickness;
  const residual = zMoment - xMoment;
  return {
    minimum_Z_resultant_separation_mm: separation,
    minimum_Z_preload_moment_Nmm: zMoment,
    maximum_opposing_X_preload_moment_Nmm: xMoment,
    signed_residual_lower_bound_Nmm: residual,
    minimum_px_over_pz_for_this_necessary_condition: separation / thickness,
    status: residual > 0
      ? "REJECTED_INTENDED_FOUR_PATCH_FRICTIONLESS_EQUILIBRIUM"
      : "INCONCLUSIVE_OTHER_EQUILIBRIUM_EQUATIONS_STILL_REQUIRED"
  };
}

/*
 * Small-deflection Euler-Bernoulli endpoint matrix, rigid root, two identical
 * leaves. Pair separation normal to the bending plane adds NO in-plane
 * rotational constraint. Separation along the desired-motion normal contributes
 * n*EA*d^2/(4L) rotational stiffness through opposing axial extension.
 * This latter term assumes a rigid tip bridge and no axial slip.
 *
 * q=[tip transverse displacement, tip rotation], contact displacement=[1,a]*q.
 * Effective contact stiffness is 1 / ([1,a] K^-1 [1,a]^T).
 * This is a limiting-case comparison, not nonlinear contact or fatigue FEA.
 */
function leafResponse({E, width, thickness, count, length, displacement,
  normalSeparation = 0, contactOverhang = 0, fixedTipRotation = false}) {
  for (const [label, value] of Object.entries(
    {E, width, thickness, count, length}
  )) positive(value, label);
  if (!Number.isInteger(count)) throw new Error("leaf count must be an integer");
  positive(displacement, "displacement", true);
  positive(normalSeparation, "normal separation", true);
  positive(contactOverhang, "contact overhang", true);
  if (typeof fixedTipRotation !== "boolean") throw new Error("rotation flag");
  const EI = E * width * thickness ** 3 / 12;
  const EA = E * width * thickness;
  const k11 = count * 12 * EI / length ** 3;
  const k12 = -count * 6 * EI / length ** 2;
  const guideK = count * EA * normalSeparation ** 2 / (4 * length);
  const k22 = count * 4 * EI / length + guideK;
  const det = k11 * k22 - k12 * k12;
  positive(det, "endpoint matrix determinant");
  let stiffness, angle;
  if (fixedTipRotation) {
    stiffness = k11;
    angle = 0;
  } else {
    const a = contactOverhang;
    stiffness = det / (k22 - 2 * a * k12 + a * a * k11);
    const force = stiffness * displacement;
    angle = force * (-k12 + a * k11) / det;
  }
  return {
    stiffness_N_per_mm: stiffness,
    force_N: stiffness * displacement,
    tip_rotation_rad: angle,
    assumed_normal_leaf_separation_mm: normalSeparation,
    contact_overhang_mm: contactOverhang,
    ideal_guidance_rotational_stiffness_Nmm_per_rad: guideK
  };
}

function analyze(files) {
  verifyBindings(files);
  const mate = files["src/masck_one/structural_frame_actuator_mates.py"].content;
  const datum = files["src/masck_one/treatment_terminal_datum_preload_v2.py"].content;
  const profile = files["studies/treatment_buttery_terminal_profile_v2.py"].content;
  const c = (s, n) => numericConstant(s, n);
  const target = c(profile, "PRELOAD_TARGET_N");
  const contact = contactCertificate({
    width: c(mate, "SHOULDER_WIDTH_MM"),
    thickness: c(mate, "SHOULDER_THICKNESS_MM"),
    masterSpan: c(datum, "MASTER_Z_X_SPAN_MM"),
    preloadSpan: c(datum, "PRELOAD_Z_X_SPAN_MM"),
    px: target, pz: target
  });
  const leaves = {};
  for (const axis of ["X", "Z"]) {
    const E = c(profile, "E_STUDY_MPA");
    const width = c(profile, "LEAF_WIDTH_MM");
    const thickness = c(profile, "LEAF_THICKNESS_MM");
    const count = c(profile, "LEAVES_PER_AXIS");
    const displacement = c(profile, axis + "_CLEARANCE_MM")
      + c(profile, "ENTRY_OVERCLOSURE_MM");
    // Reproduce axis_design() exactly. Its numerator assumes two guided leaves.
    if (count !== 2) throw new Error("axis_design numerator assumes two leaves");
    const length = Math.cbrt(2 * E * width * thickness ** 3 / (target / displacement));
    const input = {E, width, thickness, count, length, displacement};
    leaves[axis] = {
      effective_length_mm: length,
      studied_displacement_mm: displacement,
      imposed_zero_tip_rotation: leafResponse({...input, fixedTipRotation: true}),
      free_shoe_rotation: leafResponse(input),
      free_shoe_with_0p75mm_contact_overhang_DOE:
        leafResponse({...input, contactOverhang: 0.75}),
      normal_separated_0p8mm_pair_DOE:
        leafResponse({...input, normalSeparation: 0.8}),
      interpretation:
        "0.40 N requires an actual rotational constraint. The transverse V7 pair " +
        "does not supply it intrinsically. Unilateral shoe contact may constrain " +
        "rotation, but then contact moment, pressure, friction and lift-off must " +
        "be solved together. The free-shoe result is not a measured seated force.",
      physical_validation_eligible: false
    };
  }
  return {
    schema: "MASCK_ONE_TERMINAL_MECHANICS_DIAGNOSTIC",
    consumed_head: SOURCE_HEAD,
    consumed_git_blobs: BINDINGS,
    evidence_class: "ANALYTICAL_SOURCE_BOUND_IDEALIZATION",
    intended_contact_certificate: contact,
    spring_boundary_condition_comparison: leaves,
    unresolved_CAD_and_mechanics: [
      "Exact spline-fit cam normals/contact patches have not been solved here.",
      "Include all actual carrier contacts before asserting full assembly equilibrium.",
      "Resolve preload line of action and full six-component interface wrench.",
      "Define stress-free spring manufacturing geometry separately from installed deformation.",
      "Resolve root/tip rotational compliance and nonlinear unilateral contact.",
      "Evaluate the posterior ladder with bending/torsion and real joint compliance.",
      "Rebuild valid B-reps and continuous sweeps before releasing component STEP."
    ],
    digital_mechanism_closed: false,
    fusion_export_verified: false,
    physical_validation_eligible: false
  };
}

function selfTest() {
  let checks = 0;
  function assert(condition) { checks++; if (!condition) throw new Error("check " + checks); }
  function near(a, b) { assert(Math.abs(a-b) <= 1e-11 * Math.max(1, Math.abs(b))); }
  function rejects(fn) { let failed = false; try { fn(); } catch (_) { failed = true; } assert(failed); }
  const nominal = {width:8, thickness:0.8, masterSpan:1, preloadSpan:1.2, px:0.4, pz:0.4};
  const q = contactCertificate(nominal);
  near(q.signed_residual_lower_bound_Nmm, 2);
  near(q.minimum_px_over_pz_for_this_necessary_condition, 7.25);
  near(contactCertificate({...nominal, px:0.8, pz:0.8}).signed_residual_lower_bound_Nmm, 4);
  assert(contactCertificate({...nominal, masterSpan:7}).status.startsWith("INCONCLUSIVE"));
  rejects(() => contactCertificate({...nominal, thickness:0}));
  rejects(() => contactCertificate({...nominal, px:NaN}));
  const input = {E:190000, width:0.8, thickness:0.15, count:2, length:8, displacement:0.19};
  const free = leafResponse(input), guided = leafResponse({...input, fixedTipRotation:true});
  near(free.stiffness_N_per_mm / guided.stiffness_N_per_mm, 0.25);
  assert(leafResponse({...input, contactOverhang:0.75}).force_N < free.force_N);
  const separated = leafResponse({...input, normalSeparation:0.8});
  assert(separated.force_N > free.force_N && separated.force_N < guided.force_N);
  assert(separated.tip_rotation_rad < free.tip_rotation_rad);
  near(leafResponse({...input, displacement:0}).force_N, 0);
  rejects(() => leafResponse({...input, length:Infinity}));
  rejects(() => numericConstant("A = NaN\n", "A"));
  rejects(() => numericConstant("A = 1\nA = 2\n", "A"));
  rejects(() => verifyBindings({}));
  return {status:"PASS_NUMERICAL_MODEL_SELF_TESTS_ONLY", checks};
}

if (typeof module !== "undefined")
  module.exports = {analyze, selfTest, contactCertificate, leafResponse, verifyBindings, BINDINGS};

if (typeof require !== "undefined" && require.main === module) {
  const fs = require("node:fs");
  const crypto = require("node:crypto");
  const files = {};
  for (const path of Object.keys(BINDINGS)) {
    const bytes = fs.readFileSync(path);
    const header = Buffer.from("blob " + bytes.length + "\0", "utf8");
    const sha = crypto.createHash("sha1").update(header).update(bytes).digest("hex");
    files[path] = {content:bytes.toString("utf8"), git_blob_sha:sha};
  }
  const report = analyze(files);
  report.numerical_self_tests = selfTest();
  process.stdout.write(JSON.stringify(report, null, 2) + "\n");
}
