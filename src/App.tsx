import { useEffect, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Bookmark,
  BookOpen,
  Briefcase,
  Check,
  ChevronRight,
  Clock,
  Code2,
  Compass,
  Flame,
  Globe2,
  Menu,
  Network,
  Play,
  Search,
  Shield,
  ShieldCheck,
  Sparkles,
  Target,
  Terminal,
  Trophy,
  X,
} from "lucide-react";
import { courses, tracks } from "./data/courses";
import {
  applyVerifiedContent,
  type LessonPublication,
} from "./data/verified-content";
import { ContentBlocks } from "./components/ContentBlocks";
import { askSentinel, type MentorReply } from "./lib/sentinel";
import { toggle } from "./lib/store";
import { useLearnerProgress } from "./features/learning/useLearnerProgress";
import type { Course, Lesson, ProgressState } from "./types";
type Page =
  | "home"
  | "catalog"
  | "tracks"
  | "dashboard"
  | "course"
  | "lesson"
  | "labs"
  | "portfolio";
const icons: Record<string, typeof Shield> = {
  shield: Shield,
  network: Network,
  terminal: Terminal,
  radar: Target,
  siren: Flame,
  search: Search,
  crosshair: Target,
  code: Code2,
  braces: Code2,
  cloud: Globe2,
  sparkles: Sparkles,
  briefcase: Briefcase,
};
export function App() {
  const [catalog, setCatalog] = useState(courses);
  const [contentStatus, setContentStatus] = useState<
    "loading" | "ready" | "unavailable"
  >("loading");
  const [page, setPage] = useState<Page>("home");
  const [selected, setSelected] = useState(courses[0]);
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const {
    progress,
    setProgress,
    loading: progressLoading,
    error: progressError,
  } = useLearnerProgress();
  const [mentor, setMentor] = useState(false);
  const [menu, setMenu] = useState(false);
  useEffect(() => {
    let active = true;
    fetch("/api/content/catalog")
      .then(async (response) => {
        if (!response.ok) throw new Error("content API unavailable");
        return (await response.json()) as {
          publications: LessonPublication[];
        };
      })
      .then(({ publications }) => {
        if (!active) return;
        const nextCatalog = applyVerifiedContent(courses, publications);
        setCatalog(nextCatalog);
        setSelected(
          (current) =>
            nextCatalog.find((course) => course.id === current.id) ||
            nextCatalog[0],
        );
        setContentStatus("ready");
      })
      .catch(() => {
        if (active) setContentStatus("unavailable");
      });
    return () => {
      active = false;
    };
  }, []);
  const go = (p: Page) => {
    setPage(p);
    scrollTo(0, 0);
    setMenu(false);
  };
  const openCourse = (c: Course) => {
    setSelected(c);
    go("course");
  };
  const openLesson = (l: Lesson) => {
    setLesson(l);
    go("lesson");
  };
  if (progressLoading) {
    return (
      <main className="route-loading" role="status">
        Loading your persisted learner workspace…
      </main>
    );
  }
  if (progressError) {
    return (
      <main className="route-loading" role="alert">
        Your learner workspace could not be loaded. Refresh to retry. No local
        fallback was used.
      </main>
    );
  }
  return (
    <div className="app">
      <Header page={page} go={go} menu={menu} setMenu={setMenu} />
      <main>
        {page === "home" && (
          <Home
            go={go}
            openCourse={openCourse}
            catalog={catalog}
            contentStatus={contentStatus}
            progress={progress}
          />
        )}{" "}
        {page === "catalog" && (
          <Catalog catalog={catalog} openCourse={openCourse} />
        )}{" "}
        {page === "tracks" && (
          <Tracks catalog={catalog} openCourse={openCourse} />
        )}{" "}
        {page === "dashboard" && (
          <Dashboard
            catalog={catalog}
            progress={progress}
            setProgress={setProgress}
            openCourse={openCourse}
            go={go}
          />
        )}{" "}
        {page === "course" && (
          <CoursePage
            course={selected}
            progress={progress}
            setProgress={setProgress}
            openLesson={openLesson}
          />
        )}{" "}
        {page === "lesson" && lesson && (
          <LessonPage
            key={lesson.id}
            course={selected}
            lesson={lesson}
            progress={progress}
            setProgress={setProgress}
            openLesson={openLesson}
            backToCourse={() => go("course")}
          />
        )}{" "}
        {page === "labs" && (
          <Labs progress={progress} setProgress={setProgress} />
        )}{" "}
        {page === "portfolio" && (
          <Portfolio progress={progress} setProgress={setProgress} />
        )}
      </main>
      <button
        className="mentor-fab"
        onClick={() => setMentor(true)}
        aria-label="Ask Sentinel"
      >
        <Sparkles size={18} /> Ask Sentinel
      </button>
      {mentor && (
        <Mentor
          course={selected}
          lesson={
            lesson ||
            selected.modules
              .flatMap((module) => module.lessons)
              .find((item) => item.verificationStatus === "verified")
          }
          close={() => setMentor(false)}
        />
      )}
      <Footer go={go} />
    </div>
  );
}
function Header({
  page,
  go,
  menu,
  setMenu,
}: {
  page: Page;
  go: (p: Page) => void;
  menu: boolean;
  setMenu: (v: boolean) => void;
}) {
  return (
    <header>
      <button className="brand" onClick={() => go("home")}>
        <span className="brandmark">
          <ShieldCheck />
        </span>
        <span>
          CYBERMENTOR <b>AI</b>
        </span>
      </button>
      <nav className={menu ? "open" : ""}>
        {(
          [
            ["catalog", "Courses"],
            ["tracks", "Career Paths"],
            ["labs", "Labs"],
            ["portfolio", "Portfolio"],
          ] as [Page, string][]
        ).map(([p, l]) => (
          <button
            className={page === p ? "active" : ""}
            onClick={() => go(p)}
            key={p}
          >
            {l}
          </button>
        ))}
        <button className="nav-login" onClick={() => go("dashboard")}>
          Learner dashboard
        </button>
      </nav>
      <button className="menu" onClick={() => setMenu(!menu)} aria-label="Menu">
        {menu ? <X /> : <Menu />}
      </button>
    </header>
  );
}
function Home({
  go,
  openCourse,
  catalog,
  contentStatus,
  progress,
}: {
  go: (p: Page) => void;
  openCourse: (c: Course) => void;
  catalog: Course[];
  contentStatus: "loading" | "ready" | "unavailable";
  progress: ProgressState;
}) {
  const publishedLessons = catalog
    .flatMap((course) => course.modules)
    .flatMap((module) => module.lessons)
    .filter((lesson) => lesson.verificationStatus === "verified").length;
  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <div className="eyebrow">
            <span /> Built for real security work
          </div>
          <h1>
            Don’t just learn cyber.
            <br />
            <em>Become the defender.</em>
          </h1>
          <p>
            A verified-content repository, transparent adaptive sequencing, and
            a bounded mentor—without generating the curriculum at lesson load.
          </p>
          <div className="hero-actions">
            <button className="primary" onClick={() => go("tracks")}>
              Find your path <ArrowRight />
            </button>
            <button
              className="secondary"
              onClick={() => openCourse(catalog[0])}
            >
              <Play /> Check course availability
            </button>
          </div>
          <div className="proof">
            <div>
              <b>12</b>
              <span>Published courses</span>
            </div>
            <div>
              <b>{publishedLessons}</b>
              <span>Published lessons</span>
            </div>
            <div>
              <b>{contentStatus === "ready" ? "Live" : "—"}</b>
              <span>Content repository</span>
            </div>
          </div>
        </div>
        <div className="hero-panel">
          <div className="panel-top">
            <div className="status-dot" /> RECORDED LEARNER STATE
          </div>
          <h3>SOC Analyst</h3>
          <p>
            {progress.enrolledCourses.length
              ? "Your persisted academy activity"
              : "No course activity has been recorded yet"}
          </p>
          <div className="next-card">
            <span className="course-icon blue">
              <Target />
            </span>
            <div>
              <small>SERVER-OWNED PROGRESS</small>
              <b>
                {progress.enrolledCourses.length
                  ? `${progress.enrolledCourses.length} enrolled course`
                  : "Start a published course"}
              </b>
              <span>
                {progress.completedLessons.length} verified lesson completion
                {progress.completedLessons.length === 1 ? "" : "s"}
              </span>
            </div>
            <button
              aria-label="Open a published course"
              onClick={() =>
                openCourse(
                  catalog.find((course) =>
                    progress.enrolledCourses.includes(course.id),
                  ) || catalog[3],
                )
              }
            >
              <ArrowRight />
            </button>
          </div>
          <div className="sentinel-note">
            <Sparkles />
            <div>
              <b>Evidence policy</b>
              <p>
                Skill estimates appear only after diagnostic or practical
                evidence is recorded.
              </p>
            </div>
          </div>
        </div>
      </section>
      <section className="trust">
        <span>Aligned with public guidance from</span>
        <b>NIST</b>
        <b>OWASP</b>
        <b>MITRE ATT&CK</b>
        <b>CISA</b>
        <b>CIS</b>
      </section>
      <section className="section">
        <div className="section-head">
          <div>
            <span className="kicker">START WITH DIRECTION</span>
            <h2>A roadmap, not a content maze.</h2>
            <p>
              Every track connects theory, practice, evidence, and a real job
              outcome.
            </p>
          </div>
          <button className="text-btn" onClick={() => go("tracks")}>
            Explore all paths <ArrowRight />
          </button>
        </div>
        <div className="track-grid">
          {tracks.slice(0, 3).map((t) => (
            <article
              className="track-card"
              key={t.id}
              style={{ "--accent": t.color } as React.CSSProperties}
            >
              <span className="tag">{t.level}</span>
              <div className="track-icon">
                <Compass />
              </div>
              <h3>{t.title}</h3>
              <p>{t.description}</p>
              <div className="track-meta">
                <Clock /> {t.duration}
                <span>·</span>
                <BookOpen /> {t.courseIds.length} courses
              </div>
              <button onClick={() => go("tracks")}>
                View roadmap <ChevronRight />
              </button>
            </article>
          ))}
        </div>
      </section>
      <section className="dark-section">
        <span className="kicker">THE CYBERMENTOR METHOD</span>
        <h2>
          Understanding is the start.
          <br />
          Evidence is the finish.
        </h2>
        <div className="method-grid">
          {[
            [
              "01",
              "Learn deeply",
              "Clear explanations build mental models, not flashcard memory.",
            ],
            [
              "02",
              "Practice safely",
              "Guided labs use local, deliberately vulnerable or simulated targets.",
            ],
            [
              "03",
              "Think under pressure",
              "The roadmap targets workplace scenarios; executable scenario packs remain a future milestone.",
            ],
            [
              "04",
              "Prove the skill",
              "Projects and reviewed evidence are the intended path to an employer-ready portfolio.",
            ],
          ].map((x) => (
            <div key={x[0]}>
              <span>{x[0]}</span>
              <h3>{x[1]}</h3>
              <p>{x[2]}</p>
            </div>
          ))}
        </div>
      </section>
      <section className="section">
        <div className="section-head">
          <div>
            <span className="kicker">INITIAL ACADEMY</span>
            <h2>Build skills that compound.</h2>
          </div>
          <button className="text-btn" onClick={() => go("catalog")}>
            Browse all courses <ArrowRight />
          </button>
        </div>
        <div className="course-grid">
          {catalog.slice(0, 6).map((c) => (
            <CourseCard course={c} open={() => openCourse(c)} key={c.id} />
          ))}
        </div>
      </section>
    </>
  );
}
function Catalog({
  catalog,
  openCourse,
}: {
  catalog: Course[];
  openCourse: (c: Course) => void;
}) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("All");
  const cats = ["All", ...new Set(catalog.map((c) => c.category))];
  const shown = catalog.filter(
    (c) =>
      (filter === "All" || c.category === filter) &&
      (c.title + c.description + c.skills.join(" "))
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  return (
    <section className="page section">
      <span className="kicker">COURSE CATALOG</span>
      <h1>Explore the academy.</h1>
      <p className="lead">
        Original, standards-informed learning designed around what you can
        do—not how much you watched.
      </p>
      <div className="catalog-tools">
        <label>
          <Search />
          <input
            aria-label="Search courses and skills"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search courses and skills…"
          />
        </label>
        <select
          aria-label="Filter courses by category"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          {cats.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
      </div>
      <div className="result-count">{shown.length} courses</div>
      <div className="course-grid">
        {shown.map((c) => (
          <CourseCard course={c} open={() => openCourse(c)} key={c.id} />
        ))}
      </div>
    </section>
  );
}
function CourseCard({ course, open }: { course: Course; open: () => void }) {
  const Icon = icons[course.icon] || Shield;
  const publishedLessons = course.modules
    .flatMap((module) => module.lessons)
    .filter((lesson) => lesson.verificationStatus === "verified").length;
  return (
    <article
      className="course-card"
      role="button"
      tabIndex={0}
      onClick={open}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") open();
      }}
    >
      <div
        className="course-art"
        style={{
          background: `linear-gradient(135deg,${course.color}22,${course.color}08)`,
        }}
      >
        <span style={{ background: course.color }}>
          <Icon />
        </span>
        <small>{course.category}</small>
      </div>
      <div className="course-body">
        <div className="course-label">
          {course.difficulty} ·{" "}
          {publishedLessons
            ? `${publishedLessons} published lessons`
            : "PLANNED — NOT PUBLISHED"}
        </div>
        <h3>{course.title}</h3>
        <p>{course.description}</p>
        <div className="skills">
          {course.skills.slice(0, 2).map((s) => (
            <span key={s}>{s}</span>
          ))}
        </div>
        <div className="course-foot">
          <span>{publishedLessons} reviewed lessons</span>
          <span>
            {Math.ceil(
              course.modules
                .flatMap((module) => module.lessons)
                .filter((lesson) => lesson.verificationStatus === "verified")
                .reduce((total, lesson) => total + lesson.minutes, 0) / 60,
            )}{" "}
            hours of published lessons
          </span>
          <ArrowRight />
        </div>
      </div>
    </article>
  );
}
function Tracks({
  catalog,
  openCourse,
}: {
  catalog: Course[];
  openCourse: (c: Course) => void;
}) {
  return (
    <section className="page section">
      <span className="kicker">CAREER ROADMAPS</span>
      <h1>Your next role, made navigable.</h1>
      <p className="lead">
        Ordered learning, required evidence, and transparent
        prerequisites—without pretending every learner starts in the same place.
      </p>
      <div className="roadmaps">
        {tracks.map((t, ti) => (
          <article
            key={t.id}
            className="roadmap"
            style={{ "--accent": t.color } as React.CSSProperties}
          >
            <div className="roadmap-copy">
              <span className="tag">
                PATH {String(ti + 1).padStart(2, "0")}
              </span>
              <h2>{t.title}</h2>
              <p>{t.description}</p>
              <div className="track-meta">
                <Clock /> {t.duration}
                <span>·</span>
                {t.level}
              </div>
              <h4>Career outcomes</h4>
              <div className="skills">
                {t.roles.map((r) => (
                  <span key={r}>{r}</span>
                ))}
              </div>
            </div>
            <div className="roadmap-steps">
              {t.courseIds.map((id, i) => {
                const c = catalog.find((x) => x.id === id)!;
                return (
                  <button key={id} onClick={() => openCourse(c)}>
                    <i>{i + 1}</i>
                    <span>
                      <small>{c.category}</small>
                      <b>{c.shortTitle}</b>
                    </span>
                    <ChevronRight />
                  </button>
                );
              })}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
function Dashboard({
  catalog,
  progress,
  setProgress,
  openCourse,
  go,
}: {
  catalog: Course[];
  progress: ProgressState;
  setProgress: (progress: ProgressState) => void;
  openCourse: (c: Course) => void;
  go: (p: Page) => void;
}) {
  const enrolled = catalog.filter((c) =>
    progress.enrolledCourses.includes(c.id),
  );
  const done = progress.completedLessons.length;
  const nextCourse =
    enrolled.find((course) =>
      course.modules
        .flatMap((module) => module.lessons)
        .some(
          (lesson) =>
            lesson.verificationStatus === "verified" &&
            !progress.completedLessons.includes(lesson.id),
        ),
    ) || enrolled[0];
  const nextLessons = (
    nextCourse?.modules.flatMap((module) => module.lessons) || []
  ).filter((lesson) => lesson.verificationStatus === "verified");
  const nextDone = nextLessons.filter((lesson) =>
    progress.completedLessons.includes(lesson.id),
  ).length;
  const nextLesson =
    nextLessons.find(
      (lesson) => !progress.completedLessons.includes(lesson.id),
    ) || nextLessons[0];
  const nextPercent = nextLessons.length
    ? Math.round((nextDone / nextLessons.length) * 100)
    : 0;
  return (
    <section className="dashboard page section">
      <div className="dash-hello">
        <div>
          <span className="kicker">LEARNER DASHBOARD</span>
          <h1>Local learner dashboard.</h1>
          <p>
            Your progress below is calculated from this browser’s saved state.
          </p>
        </div>
        <div className="streak">
          <ShieldCheck />
          <b>Private</b>
          <span>browser-local state</span>
        </div>
      </div>
      <div className="dash-grid">
        <div className="continue">
          <span className="tag">RECOMMENDED NEXT</span>
          <h2>{nextLesson?.title || "Choose your first course"}</h2>
          <p>{nextCourse?.title || "Browse the course catalog"}</p>
          <div className="progress">
            <i style={{ width: `${nextPercent}%` }} />
          </div>
          <div>
            <span>{nextPercent}% complete</span>
            <button
              className="primary"
              onClick={() =>
                nextCourse ? openCourse(nextCourse) : go("catalog")
              }
            >
              Continue <ArrowRight />
            </button>
          </div>
        </div>
        <div className="stat">
          <Target />
          <span>Lessons completed</span>
          <b>{done}</b>
          <small>Across {enrolled.length} active courses</small>
        </div>
        <div className="stat">
          <Trophy />
          <span>Local activity records</span>
          <b>
            {progress.labCompleted.length +
              Object.keys(progress.quizScores).length}
          </b>
          <small>Not identity verified</small>
        </div>
      </div>
      <AdaptivePanel progress={progress} setProgress={setProgress} />
      <div className="section-head compact">
        <h2>Continue learning</h2>
        <button className="text-btn" onClick={() => go("catalog")}>
          Find courses <ArrowRight />
        </button>
      </div>
      <div className="enrolled-grid">
        {enrolled.map((c) => {
          const all = c.modules.flatMap((m) => m.lessons);
          const n = all.filter((l) =>
            progress.completedLessons.includes(l.id),
          ).length;
          return (
            <button key={c.id} onClick={() => openCourse(c)}>
              <span style={{ background: c.color }}>
                {Math.round((n / all.length) * 100)}%
              </span>
              <div>
                <small>{c.category}</small>
                <b>{c.title}</b>
                <div className="progress">
                  <i
                    style={{
                      width: `${(n / all.length) * 100}%`,
                      background: c.color,
                    }}
                  />
                </div>
                <em>
                  {n} of {all.length} lessons
                </em>
              </div>
              <ChevronRight />
            </button>
          );
        })}
      </div>
    </section>
  );
}
function AdaptivePanel({
  progress,
  setProgress,
}: {
  progress: ProgressState;
  setProgress: (progress: ProgressState) => void;
}) {
  type Recommendation = {
    activityId: string;
    activityType: string;
    difficulty: string;
    title: string;
    reason: string;
    hintStartLevel: number;
  };
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [notice, setNotice] = useState("Loading verified recommendations…");
  useEffect(() => {
    let active = true;
    fetch("/api/adaptive/recommendations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        skills: progress.skillStates,
        timeAvailable: 60,
      }),
    })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        return (await response.json()) as {
          recommendations: Recommendation[];
          notice: string;
        };
      })
      .then((payload) => {
        if (!active) return;
        setRecommendations(
          payload.recommendations.filter(
            (item) =>
              !progress.dismissedRecommendations.includes(item.activityId),
          ),
        );
        setNotice(payload.notice);
      })
      .catch(() => {
        if (active)
          setNotice(
            "Adaptive recommendations are unavailable; official curriculum access is unaffected.",
          );
      });
    return () => {
      active = false;
    };
  }, [progress.dismissedRecommendations, progress.skillStates]);
  return (
    <section className="adaptive-panel" aria-labelledby="adaptive-title">
      <span className="tag">RULE-BASED · VERIFIED ACTIVITIES ONLY</span>
      <h2 id="adaptive-title">Personalized next steps</h2>
      <p>{notice}</p>
      {recommendations.map((recommendation) => (
        <article key={recommendation.activityId}>
          <b>{recommendation.title}</b>
          <span>
            {recommendation.activityType} · {recommendation.difficulty}
          </span>
          <p>{recommendation.reason}</p>
          <small>
            Suggested hint start: level {recommendation.hintStartLevel}
          </small>
          <button
            className="text-btn"
            onClick={() =>
              setProgress({
                ...progress,
                dismissedRecommendations: [
                  ...new Set([
                    ...progress.dismissedRecommendations,
                    recommendation.activityId,
                  ]),
                ],
              })
            }
          >
            Dismiss recommendation
          </button>
        </article>
      ))}
    </section>
  );
}
function CoursePage({
  course,
  progress,
  setProgress,
  openLesson,
}: {
  course: Course;
  progress: ProgressState;
  setProgress: (p: ProgressState) => void;
  openLesson: (l: Lesson) => void;
}) {
  const enrolled = progress.enrolledCourses.includes(course.id);
  const publishedModules = course.modules
    .map((module) => ({
      ...module,
      lessons: module.lessons.filter(
        (lesson) => lesson.verificationStatus === "verified",
      ),
    }))
    .filter((module) => module.lessons.length);
  const lessons = publishedModules.flatMap((module) => module.lessons);
  const available = lessons.length > 0;
  const done = lessons.filter((l) =>
    progress.completedLessons.includes(l.id),
  ).length;
  const Icon = icons[course.icon] || Shield;
  return (
    <>
      <section
        className="course-hero"
        style={{ "--accent": course.color } as React.CSSProperties}
      >
        <div className="course-hero-inner">
          <div>
            <div className="breadcrumbs">
              Catalog <ChevronRight /> {course.category}
            </div>
            <span className="tag">
              {course.difficulty} ·{" "}
              {Math.ceil(
                lessons.reduce(
                  (total, lesson) => total + lesson.minutes,
                  0,
                ) / 60,
              )}{" "}
              hours of published lessons
            </span>
            <h1>{course.title}</h1>
            <p>{course.description}</p>
            <div className="skills">
              {course.skills.map((s) => (
                <span key={s}>{s}</span>
              ))}
            </div>
            <button
              className="primary"
              disabled={!available}
              onClick={() =>
                !available
                  ? undefined
                  : enrolled
                    ? openLesson(
                        lessons.find(
                          (l) => !progress.completedLessons.includes(l.id),
                        ) || lessons[0],
                      )
                    : setProgress({
                        ...progress,
                        enrolledCourses: [
                          ...progress.enrolledCourses,
                          course.id,
                        ],
                      })
              }
            >
              {!available ? (
                <>Verified lessons not yet published</>
              ) : enrolled ? (
                <>
                  <Play /> Continue learning
                </>
              ) : (
                <>
                  Enroll free <ArrowRight />
                </>
              )}
            </button>
          </div>
          <div className="course-emblem">
            <span>
              <Icon />
            </span>
            <b>{publishedModules.length}</b>
            <small>modules · {lessons.length} lessons</small>
          </div>
        </div>
      </section>
      <section className="section course-detail">
        <div className="syllabus">
          <h2>Course syllabus</h2>
          <p>
            Only independently reviewed, current publications appear below.
            Planned legacy outlines are never rendered as learner instruction.
          </p>
          {!available && (
            <div className="feedback bad" role="status">
              <b>No learner content is published for this course.</b>
              <p>
                Human authors and authorized reviewers must complete the content
                workflow before this course can be opened.
              </p>
            </div>
          )}
          {publishedModules.map((m, mi) => (
            <details key={m.id}>
              <summary>
                <span>{String(mi + 1).padStart(2, "0")}</span>
                <div>
                  <b>{m.title}</b>
                  <small>
                    {m.lessons.length} lessons ·{" "}
                    {m.lessons.reduce((a, l) => a + l.minutes, 0)} min
                  </small>
                </div>
                <ChevronRight />
              </summary>
              {m.lessons.map((l) => (
                <button onClick={() => openLesson(l)} key={l.id}>
                  <span
                    className={
                      progress.completedLessons.includes(l.id) ? "done" : ""
                    }
                  >
                    {progress.completedLessons.includes(l.id) ? (
                      <Check />
                    ) : (
                      <Play />
                    )}
                  </span>
                  <div>
                    <b>{l.title}</b>
                    <small>{l.minutes} min · knowledge check</small>
                  </div>
                  <Bookmark
                    className={progress.bookmarks.includes(l.id) ? "saved" : ""}
                  />
                </button>
              ))}
            </details>
          ))}
        </div>
        <aside className="course-aside">
          <h3>Your progress</h3>
          <div
            className="progress-ring"
            style={
              {
                "--p": `${lessons.length ? (done / lessons.length) * 360 : 0}deg`,
              } as React.CSSProperties
            }
          >
            <b>
              {lessons.length ? Math.round((done / lessons.length) * 100) : 0}%
            </b>
          </div>
          <span>
            {done} of {lessons.length} lessons complete
          </span>
          <hr />
          <h3>Project brief</h3>
          <p>{course.project}</p>
          <small>
            Open Portfolio to complete the published requirements, rubric, and
            formative submission check.
          </small>
          <div className="ethics">
            <ShieldCheck />
            <p>
              <b>Safe by design</b>Practice stays inside authorized, simulated
              environments.
            </p>
          </div>
        </aside>
      </section>
    </>
  );
}
function LessonPage({
  course,
  lesson,
  progress,
  setProgress,
  openLesson,
  backToCourse,
}: {
  course: Course;
  lesson: Lesson;
  progress: ProgressState;
  setProgress: (p: ProgressState) => void;
  openLesson: (l: Lesson) => void;
  backToCourse: () => void;
}) {
  const [choice, setChoice] = useState<number | null>(null);
  const [checkResult, setCheckResult] = useState<{
    correct: boolean;
    explanation: string;
  } | null>(null);
  const [checking, setChecking] = useState(false);
  const [note, setNote] = useState(progress.notes[lesson.id] || "");
  const publishedModules = course.modules
    .map((module) => ({
      ...module,
      lessons: module.lessons.filter(
        (candidate) => candidate.verificationStatus === "verified",
      ),
    }))
    .filter((module) => module.lessons.length);
  const all = publishedModules.flatMap((module) => module.lessons);
  const idx = all.findIndex((l) => l.id === lesson.id);
  const complete = progress.completedLessons.includes(lesson.id);
  if (lesson.verificationStatus !== "verified") {
    return (
      <section className="page section">
        <button className="back" onClick={backToCourse}>
          <ArrowLeft /> Course overview
        </button>
        <div className="feedback bad" role="alert">
          <b>Unpublished content blocked.</b>
          <p>
            This legacy outline is not approved learner material. It must pass
            source verification and independent human review before delivery.
          </p>
        </div>
      </section>
    );
  }
  async function gradeChoice() {
    if (choice === null || checking) return;
    setChecking(true);
    setCheckResult(null);
    try {
      const response = await fetch("/api/checks/grade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ questionId: lesson.check.id, choice }),
      });
      const payload = (await response.json()) as {
        correct?: boolean;
        explanation?: string;
        error?: string;
        skillTags?: string[];
        masteryEvidence?: MasteryEvidence;
      };
      if (!response.ok || typeof payload.correct !== "boolean") {
        throw new Error(payload.error || "Assessment service unavailable.");
      }
      setCheckResult({
        correct: payload.correct,
        explanation: payload.explanation || "Answer checked.",
      });
      let skillStates = progress.skillStates;
      if (payload.masteryEvidence && payload.skillTags?.length) {
        skillStates = await recordMasteryEvidence(
          progress,
          payload.skillTags,
          payload.masteryEvidence,
        );
      }
      setProgress({
        ...progress,
        skillStates,
        quizScores: {
          ...progress.quizScores,
          [lesson.check.id]: payload.correct ? 100 : 0,
        },
      });
    } catch {
      setCheckResult({
        correct: false,
        explanation:
          "The assessment service is unavailable. Your lesson was not marked complete; retry when the local API is running.",
      });
    } finally {
      setChecking(false);
    }
  }
  function persistNote() {
    setProgress({
      ...progress,
      notes: { ...progress.notes, [lesson.id]: note },
    });
  }
  function finish() {
    if (!complete && !checkResult?.correct) return;
    setProgress({
      ...progress,
      completedLessons: complete
        ? progress.completedLessons
        : [...progress.completedLessons, lesson.id],
      notes: { ...progress.notes, [lesson.id]: note },
    });
  }
  return (
    <div className="lesson-shell">
      <aside className="lesson-nav">
        <button className="back" onClick={backToCourse}>
          <ArrowLeft /> Course overview
        </button>
        <h3>{course.shortTitle}</h3>
        {publishedModules.map((m, mi) => (
          <div key={m.id}>
            <b>
              {mi + 1}. {m.title}
            </b>
            {m.lessons.map((l) => (
              <button
                className={l.id === lesson.id ? "active" : ""}
                onClick={() => openLesson(l)}
                key={l.id}
              >
                <span
                  className={
                    progress.completedLessons.includes(l.id) ? "done" : ""
                  }
                >
                  {progress.completedLessons.includes(l.id) && <Check />}
                </span>
                {l.title}
              </button>
            ))}
          </div>
        ))}
      </aside>
      <article className="lesson">
        <div className="lesson-top">
          <div className="breadcrumbs">
            {course.shortTitle} <ChevronRight /> Lesson {idx + 1}
          </div>
          <div>
            <button
              aria-label={
                progress.bookmarks.includes(lesson.id)
                  ? "Remove lesson bookmark"
                  : "Bookmark lesson"
              }
              onClick={() =>
                setProgress({
                  ...progress,
                  bookmarks: toggle(progress.bookmarks, lesson.id),
                })
              }
            >
              <Bookmark
                className={
                  progress.bookmarks.includes(lesson.id) ? "saved" : ""
                }
              />
            </button>
            <span>
              <Clock /> {lesson.minutes} min
            </span>
          </div>
        </div>
        <span className="kicker">
          LESSON {idx + 1} OF {all.length}
        </span>
        <h1>{lesson.title}</h1>
        <div className="objectives">
          <Target />
          <div>
            <b>By the end, you can</b>
            <ul>
              {lesson.objectives.map((x) => (
                <li key={x}>{x}</li>
              ))}
            </ul>
          </div>
        </div>
        {lesson.blocks?.length ? (
          <ContentBlocks blocks={lesson.blocks} />
        ) : (
          <div className="feedback bad" role="alert">
            <b>Structured lesson blocks are unavailable.</b>
            <p>This publication cannot be rendered safely.</p>
          </div>
        )}
        <div className="example">
          <span>WORKED EXAMPLE</span>
          <p>{lesson.example}</p>
        </div>
        <div className="knowledge">
          <span className="kicker">KNOWLEDGE CHECK</span>
          <h2>{lesson.check.question}</h2>
          {lesson.check.options.map((o, i) => (
            <button
              key={o}
              className={choice === i ? "chosen" : ""}
              onClick={() => {
                setChoice(i);
                setCheckResult(null);
              }}
            >
              <i>{String.fromCharCode(65 + i)}</i>
              {o}
            </button>
          ))}
          <button
            className="primary"
            disabled={choice === null || checking}
            onClick={gradeChoice}
          >
            {checking ? "Checking…" : "Check answer"}
          </button>
          {checkResult && (
            <div
              role="status"
              className={checkResult.correct ? "feedback good" : "feedback bad"}
            >
              <b>
                {checkResult.correct
                  ? "Correct — strong judgment."
                  : "Not yet — revisit the workflow."}
              </b>
              <p>{checkResult.explanation}</p>
            </div>
          )}
        </div>
        <div className="notes">
          <h3>Private notes</h3>
          <textarea
            aria-label="Private lesson notes"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            onBlur={persistNote}
            placeholder="Capture your reasoning, not just definitions…"
          />
        </div>
        <div className="references">
          <h3>
            {lesson.verificationStatus === "verified"
              ? "Verified References"
              : "References — verification pending"}
          </h3>
          {lesson.references.map((r) => (
            <a href={r.url} target="_blank" rel="noreferrer" key={r.url}>
              {r.publisher} — {r.title}
              <span>Accessed {r.accessed}</span>
            </a>
          ))}
        </div>
        <div className="lesson-actions">
          {idx > 0 && (
            <button
              className="secondary"
              onClick={() => openLesson(all[idx - 1])}
            >
              <ArrowLeft /> Previous
            </button>
          )}
          <button
            className="primary"
            disabled={!complete && !checkResult?.correct}
            onClick={() => {
              finish();
              if (idx < all.length - 1) openLesson(all[idx + 1]);
            }}
          >
            {complete
              ? "Continue"
              : checkResult?.correct
                ? "Mark complete & continue"
                : "Pass the check to continue"}{" "}
            <ArrowRight />
          </button>
        </div>
      </article>
    </div>
  );
}
function Labs({
  progress,
  setProgress,
}: {
  progress: ProgressState;
  setProgress: (p: ProgressState) => void;
}) {
  type LabSummary = {
    id: string;
    version: string;
    courseId: string;
    title: string;
    description: string;
    category: string;
    difficulty: string;
    estimatedMinutes: number;
    story: string;
    businessContext: string;
    learningObjectives: string[];
    prerequisites: string[];
    requiredSkills: string[];
    authorizedTarget: string;
    scope: string;
    safetyClassification: string;
    rulesOfEngagement: string[];
    environment: {
      type: string;
      runtime: string;
      isolated: boolean;
      networkAccess: boolean;
      externalTargets: boolean;
      supportsPause: boolean;
      supportsReset: boolean;
      expirationMinutes: number;
    };
    environmentStatus: "usable";
    instructions: string[];
    tasks: string[];
    expectedDeliverables: string[];
    evidenceRequirement: string;
    hints: { level: number; label: string; text: string }[];
    solutionAccessPolicy: string;
    debrief: string;
    reflectionPrompts: string[];
    cleanupSteps: string[];
    defensiveExplanation: string;
    portfolioSkills: string[];
    skillTags: string[];
    verificationStatus: "verified";
    publicationStatus: "published";
  };
  type LabInstance = {
    id: string;
    labId: string;
    status: "active" | "paused" | "completed" | "closed";
    expiresAt: string;
    hintsUsed: number;
    attempts: { correct: boolean; submittedAt: string }[];
    resetCount: number;
    completed: boolean;
  };
  const [labs, setLabs] = useState<LabSummary[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [instances, setInstances] = useState<Record<string, LabInstance>>({});
  const [revealedHints, setRevealedHints] = useState<
    Record<string, LabSummary["hints"]>
  >({});
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All");
  const [difficulty, setDifficulty] = useState("All");
  const [environmentType, setEnvironmentType] = useState("All");
  const [mode, setMode] = useState<"guided" | "independent">("guided");
  const [evidence, setEvidence] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [ownerId] = useState(() => {
    const existing = localStorage.getItem("cm-range-owner");
    if (existing) return existing;
    const created = `guest_${crypto.randomUUID().replaceAll("-", "")}`;
    localStorage.setItem("cm-range-owner", created);
    return created;
  });
  useEffect(() => {
    let live = true;
    fetch("/api/labs")
      .then(async (response) => {
        if (!response.ok) throw new Error();
        return (await response.json()) as { labs: LabSummary[] };
      })
      .then((payload) => {
        if (live) setLabs(payload.labs);
      })
      .catch(() => {
        if (live)
          setMessage({
            _global:
              "Practice service unavailable. Start the documented API service and retry.",
          });
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
  }, []);
  const categories = ["All", ...new Set(labs.map((lab) => lab.category))];
  const difficulties = ["All", ...new Set(labs.map((lab) => lab.difficulty))];
  const environments = [
    "All",
    ...new Set(labs.map((lab) => lab.environment.type)),
  ];
  const shownLabs = labs.filter(
    (lab) =>
      (category === "All" || lab.category === category) &&
      (difficulty === "All" || lab.difficulty === difficulty) &&
      (environmentType === "All" || lab.environment.type === environmentType) &&
      `${lab.title} ${lab.description} ${lab.category} ${lab.skillTags.join(" ")}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  async function launch(lab: LabSummary) {
    setMessage({ ...message, [lab.id]: "Launching isolated simulation…" });
    try {
      const response = await fetch("/api/labs/launch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ownerId, labId: lab.id }),
      });
      const payload = (await response.json()) as {
        instance?: LabInstance;
        error?: string;
      };
      if (!response.ok || !payload.instance) throw new Error(payload.error);
      setInstances({ ...instances, [lab.id]: payload.instance });
      setActive(lab.id);
      setMessage({ ...message, [lab.id]: "Lab session ready." });
    } catch {
      setMessage({
        ...message,
        [lab.id]: "The lab could not launch safely. No session was created.",
      });
    }
  }
  async function act(
    lab: LabSummary,
    action: "pause" | "resume" | "reset" | "close",
  ) {
    const instance = instances[lab.id];
    if (!instance) return;
    const response = await fetch("/api/labs/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ownerId, sessionId: instance.id, action }),
    });
    const payload = (await response.json()) as {
      instance?: LabInstance;
      error?: string;
    };
    if (!response.ok || !payload.instance) {
      setMessage({
        ...message,
        [lab.id]: payload.error || "Lab action failed.",
      });
      return;
    }
    setInstances({ ...instances, [lab.id]: payload.instance });
    if (action === "reset") {
      setEvidence({ ...evidence, [lab.id]: "" });
      setRevealedHints({ ...revealedHints, [lab.id]: [] });
    }
    if (action === "close") setActive(null);
    setMessage({ ...message, [lab.id]: `Lab ${action} completed.` });
  }
  async function revealHint(lab: LabSummary) {
    const instance = instances[lab.id];
    if (!instance) return;
    const level = instance.hintsUsed + 1;
    const response = await fetch("/api/labs/hint", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ownerId, sessionId: instance.id, level }),
    });
    const payload = (await response.json()) as {
      hint?: LabSummary["hints"][number];
      instance?: LabInstance;
      error?: string;
    };
    if (!response.ok || !payload.hint || !payload.instance) {
      setMessage({
        ...message,
        [lab.id]: payload.error || "Hint unavailable.",
      });
      return;
    }
    setInstances({ ...instances, [lab.id]: payload.instance });
    setRevealedHints({
      ...revealedHints,
      [lab.id]: [...(revealedHints[lab.id] || []), payload.hint],
    });
  }
  async function verify(lab: LabSummary) {
    const instance = instances[lab.id];
    if (!instance) {
      setMessage({
        ...message,
        [lab.id]: "Launch the lab before submitting evidence.",
      });
      return;
    }
    setMessage({ ...message, [lab.id]: "Checking evidence…" });
    try {
      const response = await fetch("/api/labs/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          labId: lab.id,
          sessionId: instance.id,
          ownerId,
          evidence: evidence[lab.id] || "",
        }),
      });
      const payload = (await response.json()) as {
        correct?: boolean;
        message?: string;
        error?: string;
        skillTags?: string[];
        masteryEvidence?: MasteryEvidence;
        instance?: LabInstance;
      };
      if (!response.ok || typeof payload.correct !== "boolean") {
        throw new Error(payload.error);
      }
      setMessage({ ...message, [lab.id]: payload.message || "Checked." });
      const skillStates =
        payload.masteryEvidence && payload.skillTags?.length
          ? await recordMasteryEvidence(
              progress,
              payload.skillTags,
              payload.masteryEvidence,
            )
          : progress.skillStates;
      const previousAttempt = progress.labAttempts[lab.id] || {
        correct: 0,
        incorrect: 0,
        hintsUsed: 0,
        lastAttemptAt: "",
      };
      const labAttempts = {
        ...progress.labAttempts,
        [lab.id]: {
          correct: previousAttempt.correct + (payload.correct ? 1 : 0),
          incorrect: previousAttempt.incorrect + (payload.correct ? 0 : 1),
          hintsUsed: payload.instance?.hintsUsed || instance.hintsUsed,
          lastAttemptAt: new Date().toISOString(),
        },
      };
      if (payload.instance)
        setInstances({ ...instances, [lab.id]: payload.instance });
      if (
        skillStates !== progress.skillStates ||
        labAttempts !== progress.labAttempts ||
        (payload.correct && !progress.labCompleted.includes(lab.id))
      ) {
        setProgress({
          ...progress,
          skillStates,
          labAttempts,
          labCompleted:
            payload.correct && !progress.labCompleted.includes(lab.id)
              ? [...progress.labCompleted, lab.id]
              : progress.labCompleted,
        });
      }
    } catch {
      setMessage({
        ...message,
        [lab.id]: "Verification failed safely; no completion was recorded.",
      });
    }
  }
  return (
    <section className="page section">
      <span className="kicker">SAFE PRACTICE ENVIRONMENTS</span>
      <h1>Practice where mistakes are allowed.</h1>
      <p className="lead">
        Launch original browser simulations, artifact investigations, and
        configuration exercises. Every available activity has a server-owned
        session, bounded evidence, progressive hints, reset, and defensive
        debrief.
      </p>
      <div className="range-stats" aria-label="Cyber Range summary">
        <div>
          <b>{labs.length}</b>
          <span>usable activities</span>
        </div>
        <div>
          <b>
            {
              labs.filter((lab) => lab.environment.type.includes("simulation"))
                .length
            }
          </b>
          <span>interactive simulations</span>
        </div>
        <div>
          <b>{progress.labCompleted.length}</b>
          <span>completed</span>
        </div>
        <div>
          <b>{progress.labBookmarks.length}</b>
          <span>bookmarked</span>
        </div>
      </div>
      <div className="catalog-tools range-tools">
        <label>
          <Search />
          <input
            aria-label="Search labs, skills, and categories"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search labs, skills, and categories…"
          />
        </label>
        <select
          aria-label="Filter labs by category"
          value={category}
          onChange={(event) => setCategory(event.target.value)}
        >
          {categories.map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
        <select
          aria-label="Filter labs by difficulty"
          value={difficulty}
          onChange={(event) => setDifficulty(event.target.value)}
        >
          {difficulties.map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
        <select
          aria-label="Filter labs by environment"
          value={environmentType}
          onChange={(event) => setEnvironmentType(event.target.value)}
        >
          {environments.map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
      </div>
      <div className="range-mode" role="group" aria-label="Lab support mode">
        <button
          className={mode === "guided" ? "active" : ""}
          onClick={() => setMode("guided")}
        >
          Guided mode
        </button>
        <button
          className={mode === "independent" ? "active" : ""}
          onClick={() => setMode("independent")}
        >
          Independent mode
        </button>
        <span>{shownLabs.length} matching activities</span>
      </div>
      {loading && <p role="status">Loading safe practice exercises…</p>}
      {message._global && <p role="alert">{message._global}</p>}
      {!loading && !message._global && labs.length === 0 && (
        <div className="feedback bad" role="status">
          <b>No verified labs are published.</b>
          <p>Legacy fixed exercises are blocked from learner delivery.</p>
        </div>
      )}
      <div className="lab-grid">
        {shownLabs.map((lab) => {
          const done = progress.labCompleted.includes(lab.id);
          return (
            <article key={lab.id}>
              <div className="lab-head">
                <span>
                  <Terminal />
                </span>
                <i>{lab.environment.type.replaceAll("-", " ")}</i>
              </div>
              <h3>{lab.title}</h3>
              <p>{lab.description}</p>
              <div className="track-meta">
                <Clock /> {lab.estimatedMinutes} min <span>·</span>{" "}
                {lab.difficulty} <span>·</span> {lab.category}
              </div>
              <div className="skills">
                {lab.requiredSkills.slice(0, 3).map((skill) => (
                  <span key={skill}>{skill}</span>
                ))}
              </div>
              <button
                className="lab-bookmark"
                aria-label={`${progress.labBookmarks.includes(lab.id) ? "Remove" : "Add"} ${lab.title} bookmark`}
                onClick={() =>
                  setProgress({
                    ...progress,
                    labBookmarks: toggle(progress.labBookmarks, lab.id),
                  })
                }
              >
                <Bookmark />{" "}
                {progress.labBookmarks.includes(lab.id)
                  ? "Bookmarked"
                  : "Bookmark"}
              </button>
              <button
                className={done ? "verified" : ""}
                onClick={() => launch(lab)}
              >
                {done ? (
                  <>
                    <Check /> Practice checked
                  </>
                ) : (
                  <>
                    <Play /> {instances[lab.id] ? "Resume lab" : "Launch lab"}
                  </>
                )}
              </button>
              {active === lab.id && (
                <div className="lab-exercise">
                  <div className="lab-session-bar">
                    <span>
                      Session: {instances[lab.id]?.status || "launching"}
                    </span>
                    <span>
                      Expires{" "}
                      {instances[lab.id]
                        ? new Date(
                            instances[lab.id].expiresAt,
                          ).toLocaleTimeString()
                        : "—"}
                    </span>
                  </div>
                  <h4>Story</h4>
                  <p>{lab.story}</p>
                  <h4>Business context</h4>
                  <p>{lab.businessContext}</p>
                  <h4>Objectives</h4>
                  <ul>
                    {lab.learningObjectives.map((objective) => (
                      <li key={objective}>{objective}</li>
                    ))}
                  </ul>
                  <h4>Rules of engagement</h4>
                  <ul>
                    {lab.rulesOfEngagement.map((rule) => (
                      <li key={rule}>{rule}</li>
                    ))}
                  </ul>
                  <h4>Tasks</h4>
                  <ol>
                    {lab.tasks.map((task) => (
                      <li key={task}>{task}</li>
                    ))}
                  </ol>
                  <div className="lab-actions">
                    {instances[lab.id]?.status === "active" ? (
                      <button onClick={() => act(lab, "pause")}>Pause</button>
                    ) : instances[lab.id]?.status === "paused" ? (
                      <button onClick={() => act(lab, "resume")}>Resume</button>
                    ) : null}
                    <button onClick={() => act(lab, "reset")}>Reset</button>
                    <button onClick={() => act(lab, "close")}>Close</button>
                  </div>
                  <label htmlFor={`evidence-${lab.id}`}>Evidence answer</label>
                  <input
                    id={`evidence-${lab.id}`}
                    value={evidence[lab.id] || ""}
                    onChange={(event) =>
                      setEvidence({
                        ...evidence,
                        [lab.id]: event.target.value,
                      })
                    }
                    maxLength={200}
                    autoComplete="off"
                  />
                  {mode === "guided" && (
                    <div className="progressive-hints">
                      <button
                        onClick={() => revealHint(lab)}
                        disabled={
                          (instances[lab.id]?.hintsUsed || 0) >=
                          lab.hints.length
                        }
                      >
                        Reveal hint {(instances[lab.id]?.hintsUsed || 0) + 1}
                      </button>
                      {(revealedHints[lab.id] || []).map((hint) => (
                        <p key={hint.level}>
                          <b>
                            Level {hint.level} · {hint.label}:
                          </b>{" "}
                          {hint.text}
                        </p>
                      ))}
                    </div>
                  )}
                  <button onClick={() => verify(lab)}>Verify evidence</button>
                  {message[lab.id] && <p role="status">{message[lab.id]}</p>}
                  {done && (
                    <div className="lab-debrief">
                      <h4>Defensive debrief</h4>
                      <p>{lab.debrief}</p>
                      <label htmlFor={`reflection-${lab.id}`}>
                        Reflection and portfolio note
                      </label>
                      <textarea
                        id={`reflection-${lab.id}`}
                        value={progress.labReflections[lab.id] || ""}
                        onChange={(event) =>
                          setProgress({
                            ...progress,
                            labReflections: {
                              ...progress.labReflections,
                              [lab.id]: event.target.value,
                            },
                          })
                        }
                        placeholder={lab.reflectionPrompts[0]}
                      />
                      <small>
                        Portfolio skills: {lab.portfolioSkills.join(", ")}
                      </small>
                    </div>
                  )}
                </div>
              )}
            </article>
          );
        })}
      </div>
      <div className="safety-banner">
        <ShieldCheck />
        <div>
          <h3>Authorization is not optional.</h3>
          <p>
            These Version 1 activities use server-owned browser sessions and
            bundled fictional evidence. They never accept public targets or
            arbitrary commands. They are simulations—not Docker or microVM
            machines—and are labeled accordingly.
          </p>
        </div>
      </div>
    </section>
  );
}
type MasteryEvidence = {
  sourceType: string;
  sourceId: string;
  score: number;
  independenceLevel: number;
  hintsUsed: number;
  attempts: number;
  evidenceWeight: number;
  occurredAt: string;
};
async function recordMasteryEvidence(
  progress: ProgressState,
  skillTags: string[],
  evidence: MasteryEvidence,
) {
  const updates = await Promise.allSettled(
    skillTags.map(async (skillId) => {
      const response = await fetch("/api/adaptive/mastery", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          previous: progress.skillStates[skillId] || {
            masteryEstimate: 0,
            masteryConfidence: 0,
            evidenceCount: 0,
          },
          evidence: [evidence],
        }),
      });
      if (!response.ok) throw new Error("mastery service unavailable");
      const payload = (await response.json()) as {
        skillState: ProgressState["skillStates"][string];
      };
      return [skillId, payload.skillState] as const;
    }),
  );
  const accepted = updates.flatMap((update) =>
    update.status === "fulfilled" ? [update.value] : [],
  );
  return accepted.length
    ? {
        ...progress.skillStates,
        ...Object.fromEntries(accepted),
      }
    : progress.skillStates;
}
type ProjectSummary = {
  id: string;
  version: string;
  courseId: string;
  title: string;
  scenario: string;
  requirements: string[];
  deliverables: string[];
  milestones: string[];
  rubric: {
    criterion: string;
    weight: number;
    exemplary: string;
    meets: string;
  }[];
  minimumEvidenceLength: number;
  learnerConstraints: string[];
  mentorBoundaries: string[];
  skillTags: string[];
};
function Portfolio({
  progress,
  setProgress,
}: {
  progress: ProgressState;
  setProgress: (progress: ProgressState) => void;
}) {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<Record<string, string>>({});
  const [deliverables, setDeliverables] = useState<Record<string, string[]>>(
    {},
  );
  const [messages, setMessages] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let live = true;
    fetch("/api/projects")
      .then(async (response) => {
        if (!response.ok) throw new Error();
        return (await response.json()) as { projects: ProjectSummary[] };
      })
      .then((payload) => {
        if (live) setProjects(payload.projects);
      })
      .catch(() => {
        if (live)
          setMessages({
            _global: "Project service unavailable. No submission was recorded.",
          });
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
  }, []);
  async function submit(project: ProjectSummary) {
    setMessages({ ...messages, [project.id]: "Checking project evidence…" });
    try {
      const projectEvidence =
        evidence[project.id] || progress.projectSubmissions[project.id] || "";
      const response = await fetch("/api/projects/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          projectId: project.id,
          evidence: projectEvidence,
          completedDeliverables: deliverables[project.id] || [],
        }),
      });
      const payload = (await response.json()) as {
        accepted?: boolean;
        message?: string;
        error?: string;
        skillTags?: string[];
        masteryEvidence?: MasteryEvidence;
      };
      if (!response.ok || typeof payload.accepted !== "boolean")
        throw new Error(payload.error);
      setMessages({
        ...messages,
        [project.id]: payload.message || "Project checked.",
      });
      let skillStates = progress.skillStates;
      if (payload.masteryEvidence && payload.skillTags?.length)
        skillStates = await recordMasteryEvidence(
          progress,
          payload.skillTags,
          payload.masteryEvidence,
        );
      setProgress({
        ...progress,
        skillStates,
        projectSubmissions: {
          ...progress.projectSubmissions,
          [project.id]: projectEvidence,
        },
        projectCompleted:
          payload.accepted && !progress.projectCompleted.includes(project.id)
            ? [...progress.projectCompleted, project.id]
            : progress.projectCompleted,
      });
    } catch {
      setMessages({
        ...messages,
        [project.id]:
          "Project verification failed safely; retry when the API is available.",
      });
    }
  }
  return (
    <section className="page section">
      <span className="kicker">LOCAL PRACTICE RECORD</span>
      <h1>Your work should speak for you.</h1>
      <p className="lead">
        Portfolio publishing is private by default. Export only evidence you
        have reviewed for sensitive information.
      </p>
      <div className="portfolio-summary">
        <div>
          <Trophy />
          <b>{progress.completedLessons.length}</b>
          <span>Lessons completed</span>
        </div>
        <div>
          <Terminal />
          <b>{progress.labCompleted.length}</b>
          <span>Local practice checks</span>
        </div>
        <div>
          <Target />
          <b>{Object.keys(progress.quizScores).length}</b>
          <span>Quizzes completed</span>
        </div>
        <div>
          <Briefcase />
          <b>{progress.projectCompleted.length}</b>
          <span>Projects completed</span>
        </div>
      </div>
      {loading && <p role="status">Loading Version 1 workplace projects…</p>}
      {messages._global && <p role="alert">{messages._global}</p>}
      <div className="project-grid">
        {projects.map((project) => {
          const done = progress.projectCompleted.includes(project.id);
          const checked = deliverables[project.id] || [];
          return (
            <article key={project.id}>
              <span className="tag">VERSION {project.version}</span>
              <h2>{project.title}</h2>
              <p>{project.scenario}</p>
              <button
                className={done ? "verified" : "secondary"}
                onClick={() =>
                  setActive(active === project.id ? null : project.id)
                }
              >
                {done ? (
                  <>
                    <Check /> Project completed
                  </>
                ) : (
                  <>
                    <Briefcase />{" "}
                    {active === project.id ? "Close project" : "Open project"}
                  </>
                )}
              </button>
              {active === project.id && (
                <div className="project-workspace">
                  <h3>Requirements</h3>
                  <ul>
                    {project.requirements.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                  <h3>Required deliverables</h3>
                  {project.deliverables.map((item) => (
                    <label key={item}>
                      <input
                        type="checkbox"
                        checked={checked.includes(item)}
                        onChange={() =>
                          setDeliverables({
                            ...deliverables,
                            [project.id]: toggle(checked, item),
                          })
                        }
                      />
                      {item}
                    </label>
                  ))}
                  <h3>Published rubric</h3>
                  <ul>
                    {project.rubric.map((item) => (
                      <li key={item.criterion}>
                        <b>
                          {item.criterion} ({item.weight}%)
                        </b>{" "}
                        — {item.meets}
                      </li>
                    ))}
                  </ul>
                  <label htmlFor={`project-${project.id}`}>
                    Evidence and verification summary
                  </label>
                  <textarea
                    id={`project-${project.id}`}
                    value={
                      evidence[project.id] ??
                      progress.projectSubmissions[project.id] ??
                      ""
                    }
                    onChange={(event) =>
                      setEvidence({
                        ...evidence,
                        [project.id]: event.target.value,
                      })
                    }
                    minLength={project.minimumEvidenceLength}
                    maxLength={10000}
                    placeholder={`Write at least ${project.minimumEvidenceLength} characters. Explain scope, evidence, decision, defensive action, verification, and limitations.`}
                  />
                  <button className="primary" onClick={() => submit(project)}>
                    Submit project evidence
                  </button>
                  {messages[project.id] && (
                    <p role="status">{messages[project.id]}</p>
                  )}
                </div>
              )}
            </article>
          );
        })}
      </div>
      <p className="lead">
        Version 1 project checks are formative and browser-local. They confirm
        submission completeness against the published rubric; they are not an
        identity-verified credential or a substitute for instructor review.
      </p>
    </section>
  );
}
function Mentor({
  course,
  lesson,
  close,
}: {
  course: Course;
  lesson?: Lesson;
  close: () => void;
}) {
  const [q, setQ] = useState("");
  const [messages, setMessages] = useState<{ q: string; r: MentorReply }[]>([]);
  function ask() {
    if (!q.trim()) return;
    setMessages([
      ...messages,
      { q, r: askSentinel(q, course.id, lesson?.id, lesson) },
    ]);
    setQ("");
  }
  return (
    <aside className="mentor" role="dialog" aria-label="Sentinel mentor">
      <div className="mentor-title">
        <span>
          <Sparkles />
        </span>
        <div>
          <b>SENTINEL</b>
          <small>
            <i /> Demo Mentor Mode
          </small>
        </div>
        <button onClick={close} aria-label="Close Sentinel mentor">
          <X />
        </button>
      </div>
      <div className="mentor-context">
        <BookOpen />
        {lesson?.verificationStatus === "verified" ? (
          <>
            Verified context: <b>{lesson.title}</b>
          </>
        ) : (
          <>
            <b>Verification pending</b> — Sentinel will not use this outline as
            grounded instruction.
          </>
        )}
      </div>
      <div className="messages">
        <div className="bot">
          <b>High standards. Patient instruction. No shortcuts.</b>
          <p>
            Ask me to explain a concept, challenge your reasoning, or create
            extra practice.
          </p>
        </div>
        {messages.map((m, i) => (
          <div key={i}>
            <div className="user-msg">{m.q}</div>
            <div className="bot">
              <p>{m.r.answer}</p>
              {m.r.citations.map((c) => (
                <a href={c.url} target="_blank" rel="noreferrer" key={c.url}>
                  {c.label}
                </a>
              ))}
            </div>
          </div>
        ))}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask();
        }}
      >
        <textarea
          aria-label="Question for Sentinel"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Ask a course-aware question…"
        />
        <button aria-label="Send question to Sentinel">
          <ArrowRight />
        </button>
      </form>
      <small className="mentor-foot">
        Demo mode uses approved course content and deterministic safety rules.
      </small>
    </aside>
  );
}
function Footer({ go }: { go: (p: Page) => void }) {
  return (
    <footer>
      <div className="brand">
        <span className="brandmark">
          <ShieldCheck />
        </span>
        <span>
          CYBERMENTOR <b>AI</b>
        </span>
      </div>
      <p>Learn. Defend. Investigate. Break Safely. Become Job-Ready.</p>
      <div>
        <button onClick={() => go("catalog")}>Courses</button>
        <button onClick={() => go("tracks")}>Career paths</button>
        <button onClick={() => go("labs")}>Safe labs</button>
      </div>
      <small>
        © 2026 CyberMentor AI · Educational environments only ·
        Privacy-conscious by default
      </small>
    </footer>
  );
}
