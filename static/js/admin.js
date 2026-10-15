/* Shared admin helpers, used across the admin pages (and the couple of candidate pages that also show a
   session-ID chip). Each piece quietly does nothing on a page that has no matching element, so this file is
   safe to load everywhere rather than duplicating the same ~150 lines in every template. */

function fallbackCopy(text, callback) {
    var textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.left = "-999999px";
    textArea.style.top = "-999999px";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
        document.execCommand('copy');
        if (callback) callback();
    } catch (err) {
        console.error('Fallback copy failed', err);
    }
    document.body.removeChild(textArea);
}

/* Session-ID chip: click to copy, with a brief green "Copied!" flash on the element itself. */
function copySessionId(text, triggerElem) {
    if (!text) return;
    function showFeedback() {
        if (!triggerElem) return;
        var origHtml = triggerElem.getAttribute('data-orig-html');
        if (!origHtml) {
            origHtml = triggerElem.innerHTML;
            triggerElem.setAttribute('data-orig-html', origHtml);
        }
        triggerElem.innerHTML = '<i class="bi bi-check2 text-success me-1"></i> Copied!';
        triggerElem.style.borderColor = '#10b981';
        triggerElem.style.color = '#34d399';
        setTimeout(function () {
            triggerElem.innerHTML = triggerElem.getAttribute('data-orig-html');
            triggerElem.style.borderColor = '';
            triggerElem.style.color = '';
        }, 1600);
    }
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(showFeedback).catch(function () { fallbackCopy(text, showFeedback); });
    } else {
        fallbackCopy(text, showFeedback);
    }
}

/* Member ID chips: one click copies the ID, ready to paste into a search box or an e-mail. */
document.addEventListener('click', function (e) {
    var chip = e.target.closest ? e.target.closest('.member-id[data-code]') : null;
    if (!chip) return;
    e.preventDefault(); e.stopPropagation();
    var code = chip.getAttribute('data-code');
    function done() {
        chip.classList.add('copied');
        var t = chip.innerHTML;
        chip.innerHTML = '<i class="bi bi-check2"></i> Copied';
        setTimeout(function () { chip.innerHTML = t; chip.classList.remove('copied'); }, 1300);
    }
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(code).then(done, done);
    else { var a = document.createElement('textarea'); a.value = code; document.body.appendChild(a); a.select(); try { document.execCommand('copy'); } catch (x) {} a.remove(); done(); }
}, true);

/* Unlock-attempt confirmation modal: the "Authorize & Unlock +1 Token" flow on the admin pages that have it. */
var pendingUnlockUserId = null;

function triggerUnlockCandidate(userId, candidateName) {
    pendingUnlockUserId = userId;
    var nameSpan = document.getElementById('modalTargetCandidate');
    if (nameSpan) nameSpan.textContent = candidateName || 'Candidate';
    var modalElem = document.getElementById('customUnlockModal');
    if (modalElem && typeof bootstrap !== 'undefined') {
        bootstrap.Modal.getOrCreateInstance(modalElem).show();
    }
}

document.addEventListener('DOMContentLoaded', function () {
    var confirmBtn = document.getElementById('confirmUnlockModalBtn');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', function () {
            if (!pendingUnlockUserId) return;
            confirmBtn.disabled = true;
            confirmBtn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i> Authorizing...';
            fetch('/admin/user/' + pendingUnlockUserId + '/unlock-attempt', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
                .then(function (res) { return res.json(); })
                .then(function (data) {
                    if (data.status === 'success') {
                        window.location.reload();
                    } else {
                        alert('Error: ' + (data.message || 'Could not unlock candidate attempt.'));
                        confirmBtn.disabled = false;
                        confirmBtn.innerHTML = '<i class="bi bi-unlock-fill me-1"></i> Confirm &amp; Unlock Slot';
                    }
                })
                .catch(function (err) {
                    alert('Connection Error: ' + err);
                    confirmBtn.disabled = false;
                    confirmBtn.innerHTML = '<i class="bi bi-unlock-fill me-1"></i> Confirm &amp; Unlock Slot';
                });
        });
    }

    /* Decline a pending slot request (candidate profile page). */
    var declineBtn = document.getElementById('declineSlotRequest');
    if (declineBtn) {
        declineBtn.addEventListener('click', function () {
            if (!confirm('Decline this request? The candidate will get a short e-mail.')) return;
            declineBtn.disabled = true;
            declineBtn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i> Declining...';
            fetch('/admin/slot-request/' + declineBtn.getAttribute('data-request') + '/decline', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }
            })
                .then(function (r) { return r.json(); })
                .then(function (d) {
                    if (d.status === 'success') {
                        window.location.reload();
                    } else {
                        alert(d.message || 'Could not decline the request.');
                        declineBtn.disabled = false;
                        declineBtn.innerHTML = '<i class="bi bi-x-circle me-1"></i> Decline';
                    }
                })
                .catch(function () {
                    alert('Connection error. Please try again.');
                    declineBtn.disabled = false;
                    declineBtn.innerHTML = '<i class="bi bi-x-circle me-1"></i> Decline';
                });
        });
    }
});
