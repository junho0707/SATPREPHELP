import { createClient } from "@supabase/supabase-js";
import * as fs from "fs";
import * as path from "path";
import { config } from "dotenv";

// Load .env.local
config({ path: path.join(__dirname, "../.env.local") });

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY!;

if (!SUPABASE_URL || !SUPABASE_SERVICE_KEY) {
  console.error("Missing environment variables:");
  console.error("  NEXT_PUBLIC_SUPABASE_URL:", SUPABASE_URL ? "set" : "MISSING");
  console.error("  SUPABASE_SERVICE_ROLE_KEY:", SUPABASE_SERVICE_KEY ? "set" : "MISSING");
  process.exit(1);
}

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

const BUCKET_NAME = "question-images";

// Assessment configurations
const ASSESSMENTS: Record<string, { folder: string; storagePrefix: string }> = {
  "sat-rw": { folder: "SAT_RW", storagePrefix: "SAT_RW" },
  "sat-math": { folder: "SAT_MATH", storagePrefix: "SAT_MATH" },
  "psat-nmsqt-rw": { folder: "PSAT_NMSQT_and_PSAT_10_RW", storagePrefix: "PSAT_NMSQT_RW" },
  "psat-8-9-rw": { folder: "PSAT_8_9_RW", storagePrefix: "PSAT_8_9_RW" },
};

interface Question {
  question_id: string;
  assessment: string;
  section: string;
  domain: string;
  skill: string;
  difficulty: number;
  prompt_text: string;
  question_text: string;
  answer_choices: string[];
  correct_answer: string;
  rationale: string;
  has_figure: boolean;
  figure_paths: string[];
}

async function createBucket() {
  console.log(`\n📦 Creating storage bucket: ${BUCKET_NAME}...`);

  const { data: buckets } = await supabase.storage.listBuckets();
  const bucketExists = buckets?.some((b) => b.name === BUCKET_NAME);

  if (bucketExists) {
    console.log(`   Bucket "${BUCKET_NAME}" already exists`);
    return;
  }

  const { error } = await supabase.storage.createBucket(BUCKET_NAME, {
    public: true,
    fileSizeLimit: 5 * 1024 * 1024,
  });

  if (error) {
    console.error("   Error creating bucket:", error.message);
    throw error;
  }

  console.log(`   ✅ Bucket created successfully`);
}

async function uploadImages(imagesDir: string, storagePrefix: string): Promise<Map<string, string>> {
  console.log(`\n🖼️  Uploading images from ${storagePrefix}...`);

  const imageUrlMap = new Map<string, string>();

  if (!fs.existsSync(imagesDir)) {
    console.log(`   No images directory found`);
    return imageUrlMap;
  }

  const imageFiles = fs.readdirSync(imagesDir).filter((f) => f.endsWith(".png"));
  console.log(`   Found ${imageFiles.length} images to upload`);

  let uploaded = 0;
  let skipped = 0;
  let failed = 0;

  for (const filename of imageFiles) {
    const filePath = path.join(imagesDir, filename);
    const fileBuffer = fs.readFileSync(filePath);

    const { error } = await supabase.storage
      .from(BUCKET_NAME)
      .upload(`${storagePrefix}/${filename}`, fileBuffer, {
        contentType: "image/png",
        upsert: true,
      });

    if (error) {
      if (error.message.includes("already exists")) {
        skipped++;
      } else {
        console.error(`   ❌ Failed to upload ${filename}: ${error.message}`);
        failed++;
        continue;
      }
    } else {
      uploaded++;
    }

    const { data: urlData } = supabase.storage
      .from(BUCKET_NAME)
      .getPublicUrl(`${storagePrefix}/${filename}`);

    const originalPath = `images/${filename}`;
    imageUrlMap.set(originalPath, urlData.publicUrl);

    const total = uploaded + skipped + failed;
    if (total % 20 === 0) {
      console.log(`   Progress: ${total}/${imageFiles.length}`);
    }
  }

  console.log(`   ✅ Uploaded: ${uploaded}, Skipped: ${skipped}, Failed: ${failed}`);
  return imageUrlMap;
}

async function seedQuestions(questionsPath: string, imageUrlMap: Map<string, string>) {
  console.log(`\n📝 Seeding questions...`);

  const questionsRaw = fs.readFileSync(questionsPath, "utf-8");
  const questions: Question[] = JSON.parse(questionsRaw);

  console.log(`   Found ${questions.length} questions to seed`);

  const dbQuestions = questions.map((q) => ({
    id: q.question_id,
    assessment: q.assessment,
    section: q.section,
    domain: q.domain,
    skill: q.skill,
    difficulty: q.difficulty,
    prompt_text: q.prompt_text,
    question_text: q.question_text,
    answer_choices: q.answer_choices,
    correct_answer: q.correct_answer,
    rationale: q.rationale || null,
    has_figure: q.has_figure,
    figure_paths: q.figure_paths.map((p) => imageUrlMap.get(p) || p),
  }));

  const BATCH_SIZE = 100;
  let inserted = 0;
  let failed = 0;

  for (let i = 0; i < dbQuestions.length; i += BATCH_SIZE) {
    const batch = dbQuestions.slice(i, i + BATCH_SIZE);

    const { error } = await supabase
      .from("questions")
      .upsert(batch, { onConflict: "id" });

    if (error) {
      console.error(`   ❌ Batch ${i / BATCH_SIZE + 1} failed:`, error.message);
      failed += batch.length;
    } else {
      inserted += batch.length;
    }

    console.log(`   Progress: ${inserted + failed}/${dbQuestions.length}`);
  }

  console.log(`   ✅ Inserted: ${inserted}, Failed: ${failed}`);
}

async function seedWorksheets(questionsPath: string) {
  console.log(`\n📚 Seeding worksheets...`);

  const questionsRaw = fs.readFileSync(questionsPath, "utf-8");
  const questions: Question[] = JSON.parse(questionsRaw);

  const skillSet = new Set<string>();
  const worksheets: { section: string; domain: string; skill: string; display_order: number }[] = [];

  let order = 0;
  for (const q of questions) {
    const key = `${q.section}|${q.domain}|${q.skill}`;
    if (!skillSet.has(key)) {
      skillSet.add(key);
      worksheets.push({
        section: q.section,
        domain: q.domain,
        skill: q.skill,
        display_order: order++,
      });
    }
  }

  console.log(`   Found ${worksheets.length} unique skills`);

  let inserted = 0;
  for (const ws of worksheets) {
    const { error } = await supabase
      .from("worksheets")
      .upsert(ws, { onConflict: "section,domain,skill" });
    if (!error) inserted++;
  }
  console.log(`   ✅ Inserted/Updated ${inserted}/${worksheets.length} worksheets`);
}

async function seedAssessment(assessmentKey: string) {
  const assessmentConfig = ASSESSMENTS[assessmentKey];
  if (!assessmentConfig) {
    console.error(`Unknown assessment: ${assessmentKey}`);
    console.log("Available assessments:", Object.keys(ASSESSMENTS).join(", "));
    process.exit(1);
  }

  const baseDir = path.join(__dirname, "../../scrape/output", assessmentConfig.folder);
  const questionsPath = path.join(baseDir, "questions.json");
  const imagesDir = path.join(baseDir, "images");

  if (!fs.existsSync(questionsPath)) {
    console.error(`Questions file not found: ${questionsPath}`);
    process.exit(1);
  }

  console.log(`\n🎯 Seeding: ${assessmentKey}`);
  console.log(`   Source: ${baseDir}`);

  const imageUrlMap = await uploadImages(imagesDir, assessmentConfig.storagePrefix);
  await seedQuestions(questionsPath, imageUrlMap);
  await seedWorksheets(questionsPath);
}

async function main() {
  console.log("🚀 SAT Prep Help - Database Seeder");
  console.log("===================================");

  const args = process.argv.slice(2);

  // If no args, seed all assessments
  const assessmentsToSeed = args.length > 0 ? args : Object.keys(ASSESSMENTS);

  try {
    await createBucket();

    for (const assessment of assessmentsToSeed) {
      await seedAssessment(assessment);
    }

    console.log("\n✅ Seeding complete!");
  } catch (error) {
    console.error("\n❌ Seeding failed:", error);
    process.exit(1);
  }
}

main();
