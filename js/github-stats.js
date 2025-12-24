document.addEventListener('DOMContentLoaded', () => {
    const OWNER = 'neurontechofficial';
    const REPO = 'spacecatgames';

    const container = document.getElementById('github-stats');
    if (!container) return;

    container.innerHTML = '<p>Loading GitHub stats…</p>';

    const api = (path) =>
    fetch(`https://api.github.com/repos/${OWNER}/${REPO}${path}`)
    .then(r => {
        if (!r.ok) throw new Error(`GitHub API error: ${r.status}`);
        return r.json();
    });

    /* ---------- Basic repo info ---------- */
    api('')
    .then(repo => {
        const lastUpdated = new Date(repo.pushed_at).toLocaleString();

        container.innerHTML = `
        <h3>Repository Stats</h3>
        <p><strong>Stars:</strong> ${repo.stargazers_count}</p>
        <p><strong>Forks:</strong> ${repo.forks_count}</p>
        <p><strong>Open Issues:</strong> ${repo.open_issues_count}</p>
        <p><strong>Last Updated:</strong> ${lastUpdated}</p>

        <h4>Commit Activity</h4>
        <canvas id="commit-graph" width="600" height="200"></canvas>

        <h4>Branches</h4>
        <ul id="branch-stats"><li>Loading branches…</li></ul>

        <small>
        <a href="${repo.html_url}" target="_blank">View on GitHub</a>
        </small>
        `;
    })
    .then(loadCommitGraph)
    .then(loadBranchStats)
    .catch(err => {
        console.error(err);
        container.innerHTML = '<p>Unable to load GitHub stats.</p>';
    });

    /* ---------- Commit activity graph ---------- */
    function loadCommitGraph() {
        return api('/stats/commit_activity')
        .then(data => {
            // GitHub may return 202 if still computing
            if (!Array.isArray(data)) throw new Error('Commit stats unavailable');

            const canvas = document.getElementById('commit-graph');
            if (!canvas) return;

            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            const weeks = data.slice(-26); // last ~6 months
            const max = Math.max(...weeks.map(w => w.total), 1);

            const barWidth = canvas.width / weeks.length;

            weeks.forEach((week, i) => {
                const height = (week.total / max) * (canvas.height - 20);
                ctx.fillStyle = '#4f46e5';
                ctx.fillRect(
                    i * barWidth,
                    canvas.height - height,
                    barWidth - 2,
                    height
                );
            });

            ctx.fillStyle = '#666';
            ctx.font = '12px sans-serif';
            ctx.fillText('Commits per week (last 6 months)', 10, 15);
        })
        .catch(err => {
            console.warn('Commit graph unavailable:', err);
            const canvas = document.getElementById('commit-graph');
            if (canvas) {
                const ctx = canvas.getContext('2d');
                ctx.fillStyle = '#666';
                ctx.fillText('Commit activity unavailable', 10, 20);
            }
        });
    }

    /* ---------- Per-branch stats ---------- */
    function loadBranchStats() {
        return api('/branches')
        .then(branches => {
            const list = document.getElementById('branch-stats');
            list.innerHTML = '';

            // Limit to avoid rate-limit explosions
            const limited = branches.slice(0, 5);

            limited.forEach(branch => {
                fetch(
                    `https://api.github.com/repos/${OWNER}/${REPO}/commits?sha=${branch.name}&per_page=1`
                )
                .then(r => {
                    const link = r.headers.get('Link');
                    let count = 'unknown';

                    if (link && link.includes('rel="last"')) {
                        const match = link.match(/page=(\d+)>; rel="last"/);
                        if (match) count = match[1];
                    } else {
                        count = '1';
                    }

                    const li = document.createElement('li');
                    li.textContent = `${branch.name}: ${count} commits`;
                    list.appendChild(li);
                })
                .catch(() => {
                    const li = document.createElement('li');
                    li.textContent = `${branch.name}: unavailable`;
                    list.appendChild(li);
                });
            });
        })
        .catch(err => {
            console.warn('Branch stats unavailable:', err);
            const list = document.getElementById('branch-stats');
            list.innerHTML = '<li>Branch data unavailable</li>';
        });
    }
});
