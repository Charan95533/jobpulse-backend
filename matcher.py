"""
JobPulse Skill Matcher
Computes match scores between user skills and job descriptions.
Uses fuzzy matching and synonym expansion for better results.
"""

import re
from difflib import SequenceMatcher


# Skill synonyms and expansions for better matching
SKILL_SYNONYMS = {
    "openstack": ["open stack", "osp", "rhosp", "red hat openstack"],
    "kubernetes": ["k8s", "kube", "container orchestration"],
    "docker": ["containers", "containerization", "docker engine"],
    "ansible": ["ansible playbook", "ansible automation", "configuration management"],
    "kvm": ["qemu", "qemu-kvm", "kernel virtual machine", "virtualization"],
    "nfv": ["network function virtualization", "vnf", "cnf", "virtual network function"],
    "rhel 8": ["rhel8", "rhel", "red hat enterprise linux", "redhat linux"],
    "linux": ["unix", "centos", "ubuntu", "debian", "fedora"],
    "nova": ["openstack compute", "compute service"],
    "neutron": ["openstack networking", "network service"],
    "cinder": ["block storage", "openstack storage"],
    "keystone": ["identity service", "openstack identity"],
    "heat": ["orchestration", "openstack orchestration"],
    "ironic": ["bare metal", "bare-metal", "baremetal provisioning"],
    "tripleo": ["triple-o", "director", "openstack director", "undercloud", "overcloud"],
    "5g core": ["5g", "5g nr", "5g network", "5g cnf"],
    "smf": ["session management function"],
    "upf": ["user plane function"],
    "tcp/ip": ["tcp", "networking", "ip networking", "network protocols"],
    "vlan": ["virtual lan", "network segmentation"],
    "ovs": ["open vswitch", "openvswitch", "virtual switch"],
    "wireshark": ["packet capture", "pcap", "network analysis", "packet analysis"],
    "bash": ["shell scripting", "bash scripting", "shell script"],
    "jira": ["issue tracking", "bug tracking", "atlassian"],
    "git": ["github", "gitlab", "version control", "source control"],
    "terraform": ["iac", "infrastructure as code"],
}


def normalize(text):
    """Lowercase and clean text for matching."""
    return re.sub(r'[^a-z0-9\s/+#.]', ' ', text.lower()).strip()


def expand_skill(skill):
    """Get all variations of a skill for matching."""
    key = normalize(skill)
    variations = {key}
    for base, synonyms in SKILL_SYNONYMS.items():
        if key == normalize(base) or key in [normalize(s) for s in synonyms]:
            variations.add(normalize(base))
            variations.update(normalize(s) for s in synonyms)
    return variations


def compute_match_score(user_skills, job_text):
    """
    Compute how well a job matches the user's skills.

    Returns:
        dict with:
          - score (0-100)
          - matched_skills (list of matched skill names)
          - total_skills (count of user skills checked)
    """
    if not job_text or not user_skills:
        return {"score": 0, "matched_skills": [], "total_skills": len(user_skills)}

    job_normalized = normalize(job_text)
    matched = []

    for skill in user_skills:
        variations = expand_skill(skill)
        for variant in variations:
            # Check exact phrase match
            if variant in job_normalized:
                matched.append(skill)
                break
            # Check fuzzy match for multi-word skills
            if len(variant.split()) > 1:
                words = variant.split()
                if all(w in job_normalized for w in words):
                    matched.append(skill)
                    break

    # Weighted scoring: more skills matched = higher score
    # But we also consider how important the skills are (OpenStack > Git for this profile)
    total = len(user_skills)
    if total == 0:
        return {"score": 0, "matched_skills": [], "total_skills": 0}

    raw_score = (len(matched) / total) * 100

    # Boost score if core skills are matched
    core_skills = {"openstack", "kvm", "nfv", "kubernetes", "ansible", "rhel 8", "linux"}
    core_matched = sum(1 for s in matched if normalize(s) in core_skills)
    core_boost = min(core_matched * 3, 15)  # Up to 15% boost

    score = min(round(raw_score + core_boost), 100)

    return {
        "score": score,
        "matched_skills": list(set(matched)),
        "total_skills": total,
    }


def extract_skills_from_text(text):
    """Extract recognizable skills from a job description."""
    all_skills = set()
    text_normalized = normalize(text)

    for base_skill, synonyms in SKILL_SYNONYMS.items():
        if normalize(base_skill) in text_normalized:
            all_skills.add(base_skill)
        for syn in synonyms:
            if normalize(syn) in text_normalized:
                all_skills.add(base_skill)
                break

    return list(all_skills)


# ── Quick test ──
if __name__ == "__main__":
    test_skills = ["OpenStack", "KVM", "NFV", "Ansible", "Docker",
                   "Kubernetes", "RHEL 8", "Linux", "Neutron", "Nova"]

    test_job = """
    We are looking for an OpenStack Cloud Engineer with experience in
    Red Hat OpenStack Platform (RHEL8, OSP16). Must have hands-on
    experience with KVM virtualization, Ansible automation, and
    Network Function Virtualization (NFV). Docker and Kubernetes
    knowledge is a plus. Strong Linux administration required.
    Experience with Nova compute and Neutron networking preferred.
    """

    result = compute_match_score(test_skills, test_job)
    print(f"Match score: {result['score']}%")
    print(f"Matched: {result['matched_skills']}")
    print(f"Total checked: {result['total_skills']}")
