import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
steps=[("1 Checkout","git clone","#DDEBF7"),("2 Install & Test","pytest + coverage","#DDEBF7"),("3 Bandit","static code analysis","#FBE0D3"),("4 SonarQube","scan + quality gate","#FBE0D3"),
("5 Trivy (fs)","deps, secrets, IaC","#FBE0D3"),("6 Docker Build","docker build","#DDEBF7"),("7 Trivy (image)","scan built image","#FBE0D3"),("8 Smoke Test","run + GET /health","#DDEBF7"),
("9 Push Image","to Docker Hub","#DDEBF7"),("10 Terraform","init / plan / apply","#E2EFDA"),("11 Post-Deploy","curl /health on EC2","#E2EFDA")]
fig,ax=plt.subplots(figsize=(10,6)); ax.set_xlim(0,10); ax.set_ylim(0,6.2); ax.axis("off")
pos=[]
for i,(t,s,c) in enumerate(steps):
    r,col=divmod(i,4); x=0.35+col*2.4 if r%2==0 else 0.35+(3-col)*2.4; y=4.2-r*1.7
    ax.add_patch(FancyBboxPatch((x,y),2.0,1.0,boxstyle="round,pad=0.03",fc=c,ec="black")); ax.text(x+1,y+0.65,t,ha="center",fontsize=11,fontweight="bold"); ax.text(x+1,y+0.28,s,ha="center",fontsize=9); pos.append((x,y))
for i in range(len(steps)-1):
    (x1,y1),(x2,y2)=pos[i],pos[i+1]
    if y1==y2:
        a,b=(x1+2.0,x2) if x2>x1 else (x1,x2+2.0); ax.annotate("",xy=(b,y2+0.5),xytext=(a,y1+0.5),arrowprops=dict(arrowstyle="-|>",lw=1.4))
    else: ax.annotate("",xy=(x2+1,y2+1.0),xytext=(x1+1,y1),arrowprops=dict(arrowstyle="-|>",lw=1.4))
ax.text(0.35,5.75,"Developer git push -> GitHub -> Jenkins (Jenkinsfile) triggers the pipeline",fontsize=10,style="italic")
ax.text(0.35,0.25,"Red = security gates (fail the build)   |   Green = AWS deployment stages (only when DEPLOY_TO_AWS = true)",fontsize=9)
plt.tight_layout(); plt.savefig("cicd_pipeline.png",dpi=150)
