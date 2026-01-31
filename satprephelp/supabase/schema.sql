-- SAT Prep Help Database Schema

-- Users (managed by Supabase Auth, extended with profile)
create table profiles (
  id uuid references auth.users primary key,
  display_name text,
  created_at timestamptz default now()
);

-- Questions
create table questions (
  id text primary key,
  assessment text not null,
  section text not null,
  domain text not null,
  skill text not null,
  difficulty int not null check (difficulty between 1 and 3),
  prompt_text text not null,
  question_text text not null,
  answer_choices jsonb not null,
  correct_answer text not null,
  rationale text,
  has_figure boolean default false,
  figure_paths jsonb default '[]'
);

-- Worksheets (skill groupings with optional video links)
create table worksheets (
  id uuid primary key default gen_random_uuid(),
  section text not null,
  domain text not null,
  skill text not null,
  video_url text,
  display_order int default 0
);

-- User progress on individual questions
create table user_progress (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users not null,
  question_id text references questions not null,
  completed boolean default false,
  correct boolean,
  completed_at timestamptz,
  unique(user_id, question_id)
);

-- User skill test attempts
create table test_attempts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users not null,
  section text not null,
  skill text not null,
  score int,
  total_questions int,
  time_taken_seconds int,
  answers jsonb,
  created_at timestamptz default now()
);

-- Indexes
create index idx_questions_section_domain_skill on questions(section, domain, skill);
create index idx_questions_difficulty on questions(difficulty);
create index idx_user_progress_user on user_progress(user_id);
create index idx_test_attempts_user on test_attempts(user_id);

-- Row Level Security
alter table profiles enable row level security;
alter table user_progress enable row level security;
alter table test_attempts enable row level security;

-- Policies
create policy "Users can view own profile"
  on profiles for select
  using (auth.uid() = id);

create policy "Users can update own profile"
  on profiles for update
  using (auth.uid() = id);

create policy "Users can view own progress"
  on user_progress for select
  using (auth.uid() = user_id);

create policy "Users can insert own progress"
  on user_progress for insert
  with check (auth.uid() = user_id);

create policy "Users can update own progress"
  on user_progress for update
  using (auth.uid() = user_id);

create policy "Users can view own test attempts"
  on test_attempts for select
  using (auth.uid() = user_id);

create policy "Users can insert own test attempts"
  on test_attempts for insert
  with check (auth.uid() = user_id);

-- Public read access for questions and worksheets
create policy "Anyone can view questions"
  on questions for select
  using (true);

create policy "Anyone can view worksheets"
  on worksheets for select
  using (true);

-- Function to create profile on signup
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id)
  values (new.id);
  return new;
end;
$$ language plpgsql security definer;

-- Trigger for new user signup
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();
