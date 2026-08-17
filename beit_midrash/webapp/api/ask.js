// Vercel serverless function: answers questions about the "edim zomemim"
// sugya, grounded strictly in the corpus in corpus.json. Never invents
// content beyond what's in that file - the user's explicit rule for this
// project, enforced here in the system prompt.

const corpus = require("./corpus.json");

function buildSystemPrompt() {
  const sourcesText = corpus
    .map((s) => {
      const tags = [...s.faces, ...s.genres].join(", ");
      return `[${s.layer} | ${s.reference}${tags ? " | " + tags : ""}]\n${s.content}`;
    })
    .join("\n\n---\n\n");

  return `את/ה עוזר/ת לימוד ב"בית מדרש" דיגיטלי, שעונה על שאלות בנוגע לסוגיית "עדים זוממים" (דברים יט, טו-כא) אך ורק על סמך המקורות הבאים - בלי להוסיף מידע, פרשנות, או ידע חיצוני משלך, גם אם את/ה "יודע/ת" אותו.

כללים מחייבים:
1. ענה/י אך ורק על סמך הטקסטים המובאים למטה. אל תוסיף פרשנות, סברות, או השלמות משלך.
2. בכל תשובה, ציין/י את מראה המקום המדויק של כל מקור שעליו הסתמכת (מה שמופיע בסוגריים המרובעים).
3. אם השאלה דורשת מידע שלא קיים במקורות למטה (למשל גמרא או פרשני פסוקים שעדיין לא הוזנו), אמור/אמרי זאת במפורש - "זה עוד לא נמצא במאגר" - ואל תמציא/י תשובה.
4. ענה/י בעברית, בקצרה ובבהירות.

המקורות (${corpus.length} סה"כ, מסודרים לפי שכבה היסטורית):

${sourcesText}`;
}

module.exports = async (req, res) => {
  if (req.method !== "POST") {
    res.status(405).json({ error: "method not allowed" });
    return;
  }

  const { question } = req.body || {};
  if (!question || typeof question !== "string" || !question.trim()) {
    res.status(400).json({ error: "missing question" });
    return;
  }

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    res.status(500).json({ error: "ANTHROPIC_API_KEY not configured on the server" });
    return;
  }

  try {
    const response = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: "claude-sonnet-4-5",
        max_tokens: 1024,
        system: buildSystemPrompt(),
        messages: [{ role: "user", content: question }],
      }),
    });

    if (!response.ok) {
      const errText = await response.text();
      res.status(502).json({ error: `Anthropic API error: ${response.status} ${errText}` });
      return;
    }

    const data = await response.json();
    const answer = data.content?.[0]?.text ?? "";
    res.status(200).json({ answer });
  } catch (err) {
    res.status(500).json({ error: String(err) });
  }
};
