# PAIRWISE_ROLE 宣告

> Pairwise Track：**兩個角色（Code Author + Bug Hunter）都要實作並提交**。
> 評分時，課程會**隨機抽取其中一個角色**，並與另一位同學隨機配對來評分。
> 因此請**同時宣告兩個 skill 的路徑**，格式如下（`roles` 為一個 list，含兩筆）。

<!--
GitHub Classroom starter workflow still checks the older single-role format
with root-level `role:` and `skill_path:`. Keep this compatibility block so
the current CI can locate one Pairwise skill, while the `roles:` list below
declares both required roles for the updated course spec.

Updated graders should parse the `roles:` list first. The legacy root-level
`role:` / `skill_path:` block is retained only as a fallback for older starter
checks and points to one of the two already-declared skills.
-->

roles:
  - role: code-author
    skill_path: skills/code-author-YunzhenYang-collection/
  - role: bug-hunter
    skill_path: skills/bug-hunter-YunzhenYang-collection/

role: code-author
skill_path: skills/code-author-YunzhenYang-collection/

## 規則

1. `roles` 必須同時包含 `code-author` 與 `bug-hunter` 兩筆。
2. 每筆的 `role` 只能是 `code-author` 或 `bug-hunter`，且不可重複。
3. 每個 `skill_path` 必須指向實際存在、且能被 `hermes skills list` 看到的 skill 資料夾。
4. 評分時課程會**隨機抽取其中一個角色**評分，並與另一位同學隨機配對；你無法選擇被抽到哪個角色，也無法選擇配對對象。
5. 若 `PAIRWISE_ROLE.md` 缺漏、格式錯誤、或任一 `skill_path` 不存在 / 無法被載入，Pairwise Track 視為無法評分，該 Track 0 分。

## 備註（選填）

<!-- 任何配對相關說明。注意：配對對象由課程自動隨機指派，不得私下約定。 -->
