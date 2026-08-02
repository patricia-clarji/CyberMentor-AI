import type { Course, Lesson, Module, Track } from "../types";

const accessed = "2026-07-19";
const sources = {
  NIST: {
    title: "Cybersecurity Framework 2.0",
    publisher: "NIST",
    url: "https://www.nist.gov/cyberframework",
    accessed,
  },
  CISA: {
    title: "Cross-Sector Cybersecurity Performance Goals",
    publisher: "CISA",
    url: "https://www.cisa.gov/cybersecurity-performance-goals",
    accessed,
  },
  OWASP: {
    title: "OWASP Top 10",
    publisher: "OWASP Foundation",
    url: "https://owasp.org/www-project-top-ten/",
    accessed,
  },
  MITRE: {
    title: "MITRE ATT&CK Enterprise",
    publisher: "MITRE",
    url: "https://attack.mitre.org/",
    accessed,
  },
  Python: {
    title: "Python 3 Documentation",
    publisher: "Python Software Foundation",
    url: "https://docs.python.org/3/",
    accessed,
  },
  Linux: {
    title: "Linux Documentation",
    publisher: "The Linux Kernel Organization",
    url: "https://docs.kernel.org/",
    accessed,
  },
  Cloud: {
    title: "Cloud Security Technical Reference Architecture",
    publisher: "CISA",
    url: "https://www.cisa.gov/sites/default/files/2023-05/Cloud%20Security%20Technical%20Reference%20Architecture%20v2.pdf",
    accessed,
  },
  AI: {
    title: "AI Risk Management Framework",
    publisher: "NIST",
    url: "https://www.nist.gov/itl/ai-risk-management-framework",
    accessed,
  },
};
type Spec = {
  title: string;
  short: string;
  category: string;
  description: string;
  color: string;
  icon: string;
  topics: string[][];
  skills: string[];
  source: keyof typeof sources;
  project: string;
};
const specs: Spec[] = [
  {
    title: "Cybersecurity Foundations",
    short: "Cyber Foundations",
    category: "Foundations",
    description:
      "Build the mental models, vocabulary, ethics, and risk thinking every security role needs.",
    color: "#7357ff",
    icon: "shield",
    skills: ["Risk analysis", "Threat modeling", "Security controls"],
    source: "NIST",
    project: "Create a defensible security plan for a growing clinic.",
    topics: [
      ["Security goals", "Assets, threats & vulnerabilities", "Risk decisions"],
      ["Identity & access", "Defense in depth", "Security controls"],
      ["Attack surface", "Threat modeling", "Common attack patterns"],
      ["Frameworks & ethics", "Security careers", "Security program briefing"],
    ],
  },
  {
    title: "Networking for Cybersecurity",
    short: "Network Security",
    category: "Networking",
    description:
      "Understand how systems communicate and investigate traffic with a defender’s eye.",
    color: "#00a9c7",
    icon: "network",
    skills: ["TCP/IP", "Packet analysis", "Segmentation"],
    source: "CISA",
    project: "Design and defend a segmented network for a small business.",
    topics: [
      ["OSI & TCP/IP", "Ethernet, MAC & ARP", "IPv4, IPv6 & subnetting"],
      ["Routing & NAT", "TCP & UDP", "DNS & DHCP"],
      ["HTTP & TLS", "Firewalls", "Network segmentation"],
      ["Packet analysis", "Network attack patterns", "Defensive investigation"],
    ],
  },
  {
    title: "Linux for Cybersecurity Professionals",
    short: "Linux Security",
    category: "Systems",
    description:
      "Operate, investigate, automate, and harden Linux systems safely.",
    color: "#f7a928",
    icon: "terminal",
    skills: ["Linux permissions", "Log analysis", "Bash"],
    source: "Linux",
    project: "Harden and document a simulated Linux web server.",
    topics: [
      ["Shell & filesystem", "Users & groups", "Permissions"],
      ["Processes & services", "Package management", "Networking commands"],
      ["Linux logs", "Bash foundations", "Safe troubleshooting"],
      ["System hardening", "Configuration review", "Incident investigation"],
    ],
  },
  {
    title: "Introduction to Security Operations and SOC Analysis",
    short: "SOC Analysis",
    category: "Blue Team",
    description:
      "Triage alerts, analyze evidence, and communicate decisions like a junior SOC analyst.",
    color: "#2f7cf6",
    icon: "radar",
    skills: ["Alert triage", "SIEM", "Case documentation"],
    source: "MITRE",
    project: "Investigate and report a multi-stage account compromise.",
    topics: [
      ["SOC mission & roles", "Events, alerts & logs", "SIEM fundamentals"],
      ["Detection rules", "IOC versus behavior", "MITRE ATT&CK mapping"],
      ["Triage workflow", "False positives", "Escalation decisions"],
      [
        "Case documentation",
        "Stakeholder communication",
        "SOC shift simulation",
      ],
    ],
  },
  {
    title: "Incident Response Foundations",
    short: "Incident Response",
    category: "Blue Team",
    description:
      "Prepare for, contain, eradicate, and learn from security incidents.",
    color: "#ed5565",
    icon: "siren",
    skills: ["Incident triage", "Containment", "Playbooks"],
    source: "NIST",
    project: "Build and exercise an account-compromise response playbook.",
    topics: [
      ["Preparation", "Detection & analysis", "Evidence preservation"],
      ["Scoping incidents", "Containment strategy", "Eradication"],
      ["Recovery", "Ransomware response", "Account compromise"],
      ["Communication", "Lessons learned", "Playbook exercise"],
    ],
  },
  {
    title: "Digital Forensics Foundations",
    short: "Digital Forensics",
    category: "Investigation",
    description:
      "Preserve evidence and reconstruct events using repeatable forensic reasoning.",
    color: "#9c5de8",
    icon: "search",
    skills: ["Chain of custody", "Timeline analysis", "Forensic reporting"],
    source: "CISA",
    project:
      "Reconstruct a simulated insider incident from an evidence bundle.",
    topics: [
      ["Forensic principles", "Evidence integrity", "Chain of custody"],
      ["Disk & file systems", "Hashing", "Metadata"],
      ["Timeline analysis", "Windows & Linux artifacts", "Browser artifacts"],
      ["Memory overview", "Evidence synthesis", "Forensic reporting"],
    ],
  },
  {
    title: "Ethical Hacking and Penetration Testing Foundations",
    short: "Ethical Hacking",
    category: "Offensive Security",
    description:
      "Learn authorized assessment methodology with defender visibility and professional reporting.",
    color: "#ff6b3d",
    icon: "crosshair",
    skills: ["Scoping", "Validation", "Security reporting"],
    source: "OWASP",
    project:
      "Conduct and report an authorized assessment of a simulated target.",
    topics: [
      [
        "Authorization & scope",
        "Rules of engagement",
        "Assessment methodology",
      ],
      ["Lab reconnaissance", "Safe enumeration", "Vulnerability validation"],
      [
        "Exploitation concepts",
        "Privilege boundaries",
        "Lateral movement concepts",
      ],
      ["Risk communication", "Remediation", "Retesting & reporting"],
    ],
  },
  {
    title: "Web Application Security Foundations",
    short: "Web App Security",
    category: "Application Security",
    description:
      "Find, explain, and remediate common web risks in deliberately vulnerable applications.",
    color: "#00b894",
    icon: "code",
    skills: ["HTTP security", "Web testing", "Secure remediation"],
    source: "OWASP",
    project: "Assess and remediate a vulnerable training application.",
    topics: [
      ["Web architecture", "HTTP, cookies & sessions", "Authentication"],
      ["Authorization", "Input validation", "SQL injection"],
      ["Cross-site scripting", "CSRF", "SSRF concepts"],
      ["File upload risk", "Security headers", "OWASP risk review"],
    ],
  },
  {
    title: "Python for Cybersecurity",
    short: "Python Security",
    category: "Engineering",
    description:
      "Write safe, tested automation for parsing, investigation, and defensive workflows.",
    color: "#3977d5",
    icon: "braces",
    skills: ["Python", "Log parsing", "Defensive automation"],
    source: "Python",
    project: "Build a tested command-line log triage tool.",
    topics: [
      ["Python foundations", "Files & paths", "JSON & CSV"],
      ["Regular expressions", "Parsing logs", "Error handling"],
      ["HTTP clients", "Hashing", "Safe API use"],
      ["CLI tools", "Testing", "Secure defensive automation"],
    ],
  },
  {
    title: "Cloud Security Foundations",
    short: "Cloud Security",
    category: "Cloud",
    description:
      "Apply identity-first controls across cloud services, workloads, and operations.",
    color: "#29a3ef",
    icon: "cloud",
    skills: ["Cloud IAM", "Cloud logging", "Key management"],
    source: "Cloud",
    project: "Threat-model and secure a multi-tier cloud workload.",
    topics: [
      ["Shared responsibility", "Cloud IAM", "Cloud networking"],
      ["Storage security", "Secrets", "Encryption & keys"],
      ["Logging & monitoring", "Misconfiguration", "Workload identity"],
      ["Containers", "Cloud incident response", "Multi-cloud principles"],
    ],
  },
  {
    title: "AI and LLM Security Foundations",
    short: "AI Security",
    category: "Emerging Tech",
    description:
      "Threat-model AI applications and design defenses against model and agent risks.",
    color: "#d44fd8",
    icon: "sparkles",
    skills: ["AI threat modeling", "Prompt injection defense", "AI evaluation"],
    source: "AI",
    project: "Threat-model and evaluate a RAG-enabled support assistant.",
    topics: [
      ["AI application architecture", "Model threats", "AI threat modeling"],
      ["Prompt injection", "Indirect injection", "Data leakage"],
      ["RAG poisoning", "Tool abuse", "Excessive agency"],
      ["Output handling", "Guardrails & monitoring", "AI red-team evaluation"],
    ],
  },
  {
    title: "Cybersecurity Career and Interview Preparation",
    short: "Career Launchpad",
    category: "Career",
    description:
      "Turn technical learning into credible evidence, clear communication, and job readiness.",
    color: "#ee8f2a",
    icon: "briefcase",
    skills: ["Career planning", "Technical writing", "Interview reasoning"],
    source: "CISA",
    project: "Publish a role-aligned portfolio case study and interview brief.",
    topics: [
      ["Role selection", "Skill mapping", "Evidence planning"],
      ["Resume projects", "Portfolio design", "Professional reports"],
      ["Technical interviews", "Behavioral interviews", "Reasoning aloud"],
      ["Ethical job search", "Continuous learning", "Career action plan"],
    ],
  },
];

function expectedChoice(
  courseIndex: number,
  moduleIndex: number,
  lessonIndex: number,
) {
  return (courseIndex + moduleIndex + lessonIndex) % 4;
}
function makeLesson(
  course: string,
  moduleTitle: string,
  topic: string,
  index: number,
  moduleIndex: number,
  courseIndex: number,
  source: keyof typeof sources,
): Lesson {
  const id = `${course}-${moduleTitle}-${topic}`
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  const checkId = `${course}-m${moduleIndex + 1}-l${index + 1}-check`;
  const options = [
    "Act on the first assumption",
    "Disable every connected service",
    "Copy a checklist without context",
  ];
  options.splice(
    expectedChoice(courseIndex, moduleIndex + 1, index + 1),
    0,
    "Define scope and preserve relevant evidence",
  );
  return {
    id,
    title: topic,
    contentVersion: "0.0.0-legacy",
    verificationStatus: "legacy-unverified",
    retrievedAt: accessed,
    minutes: 12 + index * 3,
    objectives: [
      `Explain ${topic.toLowerCase()} in clear operational terms`,
      `Apply ${topic.toLowerCase()} to a safe workplace scenario`,
      `Recognize a common failure and select a defensible control`,
    ],
    content: [
      `${topic} is best understood as a decision-making tool, not a term to memorize. Security practitioners connect the concept to an asset, a threat, an observable condition, and a proportionate response. This lesson builds that chain so you can explain both what happened and why the response is justified.`,
      `In practice, begin by defining scope and assumptions. Gather evidence without changing the environment unnecessarily, distinguish confirmed facts from hypotheses, then record the decision and its limits. Strong security work is repeatable: another analyst should be able to follow your reasoning from evidence to conclusion.`,
      `A useful control must reduce a specific risk and produce evidence that it works. Prevention alone is insufficient; pair it with visibility, a response path, and a verification step. Offensive techniques in this course remain confined to owned training environments and always include detection, remediation, and cleanup.`,
    ],
    keyTerms: [topic, "evidence", "scope", "control"],
    example: `A team observes an unexpected event related to ${topic.toLowerCase()}. Instead of reacting to the label, the analyst confirms scope, preserves relevant evidence, tests the least disruptive explanation, applies a bounded control, and documents how the team will verify recovery.`,
    check: {
      id: checkId,
      question: `What is the strongest first move when applying ${topic.toLowerCase()}?`,
      options,
    },
    references: [sources[source]],
  };
}
function makeModules(courseId: string, courseIndex: number, s: Spec): Module[] {
  return s.topics.map((topics, mi) => {
    const title =
      ["Understand", "Observe", "Practice", "Demonstrate"][mi] +
      " — " +
      topics[0];
    return {
      id: `${courseId}-m${mi + 1}`,
      title,
      description: `Develop practical judgment across ${topics.join(", ")}.`,
      lessons: topics.map((t, i) =>
        makeLesson(courseId, title, t, i, mi, courseIndex, s.source),
      ),
      quiz: topics.map((t, i) => ({
        id: `${courseId}-m${mi + 1}-q${i + 1}`,
        question: `Which approach best demonstrates sound practice for ${t}?`,
        options: [
          "Trust assumptions",
          "Use scoped evidence and verify the outcome",
          "Skip documentation",
          "Use the broadest possible intervention",
        ],
      })),
    };
  });
}
export const courses: Course[] = specs.map((s, i) => {
  const id = `course-${i + 1}`;
  return {
    id,
    title: s.title,
    shortTitle: s.short,
    category: s.category,
    description: s.description,
    difficulty: i < 3 ? "Beginner" : i > 9 ? "Intermediate" : "Beginner",
    color: s.color,
    icon: s.icon,
    skills: s.skills,
    modules: makeModules(id, i + 1, s),
    project: s.project,
  };
});
export const tracks: Track[] = [
  {
    id: "beginner",
    title: "Cybersecurity Beginner",
    description:
      "Build durable foundations, systems fluency, and your first evidence-backed portfolio.",
    duration: "4–6 months",
    level: "No experience required",
    color: "#7357ff",
    courseIds: ["course-1", "course-2", "course-3", "course-12"],
    roles: ["Security support", "Junior security analyst"],
  },
  {
    id: "soc",
    title: "SOC Analyst",
    description:
      "Learn traffic, alert triage, detection reasoning, and professional case handling.",
    duration: "5–7 months",
    level: "Beginner friendly",
    color: "#2f7cf6",
    courseIds: ["course-1", "course-2", "course-3", "course-4", "course-5"],
    roles: ["SOC Analyst I", "Cyber defense analyst"],
  },
  {
    id: "pentest",
    title: "Penetration Tester",
    description:
      "Develop authorized assessment skills with equal attention to evidence and remediation.",
    duration: "7–9 months",
    level: "Foundation required",
    color: "#ff6b3d",
    courseIds: [
      "course-1",
      "course-2",
      "course-3",
      "course-7",
      "course-8",
      "course-9",
    ],
    roles: ["Junior penetration tester", "Security consultant"],
  },
  {
    id: "cloud",
    title: "Cloud Security Engineer",
    description:
      "Combine identity, engineering, monitoring, and incident response in cloud environments.",
    duration: "6–8 months",
    level: "Intermediate",
    color: "#29a3ef",
    courseIds: ["course-1", "course-2", "course-9", "course-10", "course-5"],
    roles: ["Cloud security analyst", "Cloud security engineer"],
  },
  {
    id: "ai",
    title: "AI Security Engineer",
    description:
      "Secure AI-enabled systems with grounded threat modeling, testing, and monitoring.",
    duration: "5–7 months",
    level: "Intermediate",
    color: "#d44fd8",
    courseIds: ["course-1", "course-8", "course-9", "course-10", "course-11"],
    roles: ["AI security engineer", "Product security engineer"],
  },
];
export const domains = [
  "Cybersecurity Foundations",
  "Computer Networking",
  "Linux for Cybersecurity",
  "Windows and Active Directory",
  "Python for Cybersecurity",
  "Bash and PowerShell",
  "Security Operations Center",
  "Security Monitoring",
  "SIEM and Log Analysis",
  "Incident Response",
  "Digital Forensics",
  "Network Forensics",
  "Endpoint Forensics",
  "Memory Forensics",
  "Threat Intelligence",
  "Threat Hunting",
  "Malware Analysis Foundations",
  "Reverse Engineering Foundations",
  "Penetration Testing",
  "Web Application Security",
  "API Security",
  "Mobile Application Security",
  "Wireless Security",
  "Active Directory Security",
  "Cloud Security",
  "AWS Security",
  "Azure Security",
  "Google Cloud Security",
  "Container and Kubernetes Security",
  "DevSecOps",
  "Secure Software Development",
  "Application Security",
  "Cryptography Foundations",
  "Identity and Access Management",
  "Governance, Risk, and Compliance",
  "Security Auditing",
  "Privacy and Data Protection",
  "AI Security",
  "LLM Security",
  "IoT and Embedded Security",
  "Operational Technology Security",
  "Security Architecture",
  "Zero Trust",
  "Business Continuity",
  "Disaster Recovery",
  "Social Engineering Awareness",
  "Cybersecurity Leadership",
  "CISO Foundations",
  "Cybersecurity Interview Preparation",
  "Security Research and Responsible Disclosure",
];
