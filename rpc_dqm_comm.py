#! /usr/bin/env python

# From where to download files: https://cmsweb.cern.ch/dqm/online/data/browse/Original/00033xxxx/0003395xx/

import sys, os
import urllib.request
import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.gStyle.SetOptStat(0)

 
def getall(d, basepath="/"):
    # original: https://pastebin.com/GebcyHY9
    for key in d.GetListOfKeys():
        kname = key.GetName()
        if key.IsFolder():
            # TODO: -> "yield from" in Py3
            for i in getall(d.Get(kname), basepath+kname+"/"):
                yield i
        else:
            if (not kname.startswith(r"<")) and (not kname.startswith(r"readoutErrors")) and (not kname.startswith(r"record")) and (not kname.startswith(r"RPCEvents")): # dirty trick
                yield basepath+kname, d.Get(kname)


def histogram_object(kname, run_number, ref_run_number):
    base = kname.split(r"/")[-1]
    measurable = base.split(r"_")[0]
    disk_wheel = base.split(r"_")[1]
    if disk_wheel == r"W+0":
        disk_wheel = r"W0"
    region = "barrel" if disk_wheel.startswith("W") else "endcap"
    station = base.split(r"_")[2]
    sector = base.split(r"_")[3][-2:]

    histo = {
        'path': kname,
        'ref_path': kname.replace(run_number, ref_run_number),
        'region' : region,
        'disk_wheel' : disk_wheel,
        'station' : station,
        'sector' : sector,
        'measurable' : measurable,
    }
    return histo

def createRatio(h1, h2):
    h3 = h1.Clone("h3")
    h3.SetLineColor(ROOT.kBlack)
    h3.SetMarkerStyle(21)
    h3.SetTitle("")
    h3.SetMinimum(0)
    h3.SetMaximum(2.1)
    # Set up plot for markers and errors
    h3.Sumw2()
    h3.SetStats(0)
    h3.Divide(h2)

    # Adjust y-axis settings
    y = h3.GetYaxis()
    y.SetTitle("Ratio")
    y.SetNdivisions(505)
    y.SetTitleSize(20)
    y.SetTitleFont(43)
    y.SetTitleOffset(1.55)
    y.SetLabelFont(43)
    y.SetLabelSize(15)

    # Adjust x-axis settings
    x = h3.GetXaxis()
    x.SetTitleSize(20)
    x.SetTitleFont(43)
    x.SetTitleOffset(4.0)
    x.SetLabelFont(43)
    x.SetLabelSize(15)

    return h3

def createCanvasPads(name):
    c = ROOT.TCanvas(name, "canvas", 800, 800)
    # Upper histogram plot is pad1
    pad1 = ROOT.TPad("pad1", "pad1", 0, 0.3, 1, 1.0)
    pad1.SetBottomMargin(0)  # joins upper and lower plot
    pad1.SetGridx()
    pad1.SetGridy()
    pad1.Draw()
    # Lower ratio plot is pad2
    c.cd()  # returns to main canvas before defining pad2
    pad2 = ROOT.TPad("pad2", "pad2", 0, 0.05, 1, 0.3)
    pad2.SetTopMargin(0)  # joins upper and lower plot
    pad2.SetBottomMargin(0.2)
    pad2.SetGridx()
    pad2.SetGridy()
    pad2.Draw()

    return c, pad1, pad2
 
 
def ratioplot(histo, h1, h2, run_number, ref_run_number):
    

    # create required parts
    h3 = createRatio(h1, h2)
    c, pad1, pad2 = createCanvasPads(histo["path"])



    # draw everything
    pad1.cd()



    h1.SetLineColor(ROOT.kRed)
    h1.SetLineWidth(3)
    h2.SetLineColor(ROOT.kBlue)
    h2.SetLineWidth(3)


    hs = ROOT.THStack("hs",histo['measurable']+" - "+histo['disk_wheel']+"_"+histo['station']+"_S"+histo['sector']+";;a.u.")
    hs.Add(h1)
    hs.Add(h2)


    hs.Draw("NOSTACK hist")

    # h1.Draw("hist")
    # h2.Draw("hist same")

    # to avoid clipping the bottom zero, redraw a small axis
    # h1.GetYaxis().SetLabelSize(0.0)
    # axis = ROOT.TGaxis(-5, 20, -5, 220, 20, 220, 510, "")
    # axis.SetLabelFont(43)
    # axis.SetLabelSize(15)
    # axis.Draw()
    leg = ROOT.TLegend(.73,.62,.97,.83)
    leg.SetBorderSize(0)
    leg.SetFillColor(ROOT.kWhite)
    leg.SetFillStyle(0)
    leg.SetTextFont(60)
    leg.SetTextSize(0.04)

    leg.AddEntry(h1,"Run: "+ run_number,"L")
    leg.AddEntry(h2,"Ref. Run: "+ ref_run_number,"L")
    leg.Draw()
    pad1.Update()

    pad2.cd()
    h3.Draw("ep")

    image_path = "images/"+histo['disk_wheel']+"_"+histo['station']+"_S"+histo['sector']
    os.system("mkdir -p "+image_path)
    image_path += "/"+histo['disk_wheel']+"_"+histo['station']+"_S"+histo['sector']+"_"+histo['measurable']
    c.SaveAs(image_path+".png")
    c.SaveAs(image_path+".pdf")

    ks_test = h1.KolmogorovTest(h2)	

    return ks_test





def get_histograms(histo, dqm_file, ref_dqm_file):
    histogram = dqm_file.Get(histo['path'])
    if histogram.Integral() != 0:
        histogram.Scale(1/histogram.Integral())

    ref_histogram = ref_dqm_file.Get(histo['ref_path'])
    if ref_histogram.Integral() != 0:
        ref_histogram.Scale(1/ref_histogram.Integral())

    return histo, histogram, ref_histogram

 
## Loop over the file content
fname = sys.argv[1]
ref_fname = sys.argv[2]

run_number = fname.split(r".root")[0][-6:]
ref_run_number = ref_fname.split(r".root")[0][-6:]


dqm_file = ROOT.TFile(fname)
ref_dqm_file = ROOT.TFile(ref_fname)

list_of_histograms = []

for k, o in getall(dqm_file):
    t = o.ClassName()
    if t == "TH1F" and "AllHits/" in k and ("SummaryHistogram" not in k):
        list_of_histograms.append(histogram_object(k, run_number, ref_run_number))
        
os.system("rm -rf images ; mkdir images")
ks_probs = {}
for h in list_of_histograms:
    ks_probs[h['disk_wheel']+"_"+h['station']+"_S"+h['sector']+"_"+h['measurable']] = ratioplot(*get_histograms(h, dqm_file, ref_dqm_file), run_number, ref_run_number)


# Save KS Tests results
import json
print(ks_probs)
os.system("rm -rf ks_probs.json")
with open('ks_probs.json', 'w') as fp:
    json.dump(ks_probs, fp)
