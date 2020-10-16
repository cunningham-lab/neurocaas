import script_doc_utils

if __name__ == "__main__":
    md = script_doc_utils.initialize_doc()
    md.new_list(["NIST Model of the cloud: on demand network access to shared pool of configurale computing resources.",
        "Cloud services can be thought of as layers: SaaS, PaaS, IaaS","Cloud Native services: Infrastructure as Code, DevOps, Pets vs. Cattle, Service-based architecture: these are all part of the same web of things, just based on the idea of separating design from application. This is a big, cloud exclusive benefit."])
    md.new_line("Cloud Pros")
    md.new_list(["Ability to do lots without managing infrastructure", "Almost infinite expandability", "Specialized hardware (TPU, lambda, etc)"])
    md.new_line("Cloud Cons")
    md.new_list(["Multi-Cloud is the workst practice- vendor lock in.","Lack of control","expensive","Cortex Technical + Cost Comparison", "batch schedulers issues? They mention that networking instances is an issue but I don't think this is true: how about auto scaling groups? You can also launch in a specific subregion now from API, I think, and machines are networked at very fast speeds.","not actually infinite"])
    md.new_line("Columbia Advantages")
    md.new_list(["Direct Connect: faster network","Internet2 egress discount for researchers (see wiki)","Linkedin Learning","Access to representatives"])
    md.new_line("AWS Basics: Regions + Availability Zones. us-east-1 is peered with columbia via direct connect, so we get speed boost here! ")
    md.new_line("Data Transfer Costs: Pretty sure you're just going to need to have changes between s3 and you. EC2<->S3 does not cost money. EC2 scp also does not cost money, I think. This is not accurate.")
    md.new_line("S3 coverage and pitfalls (cost) ")
    md.new_line("EC2 coverage,`spot,reserved, ondemand`")
    md.new_line("shhgit live! is a good way to check for secrets.")
    md.new_line("Lambda is cool")
    md.new_line("Look into noisy neighbors: other jobs run on a vm. If needed, you can distribute your stuff differently.")
    md.new_line("Lack of hard limits is real, it does lag. This is a really good point. Apparently Azure has hard limits!")
    md.new_paragraph("Use experiences/alternatives")
    md.new_line("Columbia alternatives:")
    md.new_list(["Habanero/Terremoto Clusters (CUIT), Axon GPU Cluster (ZI). ","Engram for file storage.","Cortex: VMware cluster. No GPUs, but no root."])
    md.new_line("In general, this was a very high level overview, without too much specific information on the actual way to get started. ")



    md.create_md_file()
