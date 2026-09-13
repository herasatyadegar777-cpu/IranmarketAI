package com.iranmarketai.app;
import android.content.*; import android.graphics.*; import android.view.*; import java.util.*;
public class ChartView extends View{
 Paint p=new Paint(1); ArrayList<Double> values=new ArrayList<>();
 public ChartView(Context c){super(c);p.setStrokeWidth(5);setBackgroundColor(Color.rgb(248,249,251));}
 public void setValues(ArrayList<Double> v){values=v;invalidate();}
 protected void onDraw(Canvas c){super.onDraw(c); if(values==null||values.size()<2)return; double min=Collections.min(values),max=Collections.max(values); float w=getWidth(),h=getHeight();p.setColor(Color.rgb(21,101,192));p.setStyle(Paint.Style.STROKE);Path path=new Path();for(int i=0;i<values.size();i++){float x=i*w/(values.size()-1);float y=(float)(h-30-(values.get(i)-min)/(Math.max(0.0001,max-min))*(h-60));if(i==0)path.moveTo(x,y);else path.lineTo(x,y);}c.drawPath(path,p);p.setStyle(Paint.Style.FILL);p.setColor(Color.DKGRAY);p.setTextSize(28);c.drawText(String.format(Locale.US,"%.2f",max),12,28,p);c.drawText(String.format(Locale.US,"%.2f",min),12,h-8,p);}
}