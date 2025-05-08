import os
from pprint import pprint
import opensim as osim
import datetime
import xml.etree.ElementTree as ET
import numpy as np
import copy
osim.Logger.setLevelString('Trace')

def scaleModel_function(settings):
    
    path_comak_model = os.path.abspath(settings.model_dir+'/lenhart2015.osim')

    path_scaling = os.path.abspath(settings.model_dir +'/' +settings.subjID+'_rescaling_setup.xml')
    path_scaling_mod = os.path.abspath(settings.model_dir + '/'+settings.subjID+'_modified_rescaling.xml')

    # path_markers = os.path.abspath(settings.model_dir + '/Anna_v7_markerset_May_16_2023.osim')
    # path_markers = os.path.abspath(settings.model_dir + '/Anna_v7_markerset_September_15_2023.osim')

    # path_markers = os.path.abspath(settings.model_dir + '/Anna_revisedMarkers2.osim')
    path_markers = os.path.abspath(settings.model_dir + '/ISMRM_revisedMarkers_rev2.osim')


    name_model_new_markers = settings.subjID+'_lenhart_newMarkers.osim'
    path_model_new_markers = os.path.abspath(settings.model_dir + '/' + name_model_new_markers)

    # path_model_scaled_wrapped = os.path.abspath(settings.model_dir + '/scaled_lenhart_model_updated_wrap.osim')

    ## Modify Scaling Factors in OSIM Model XML from AddBiomechanics XML ##

    file = ET.parse(path_scaling)
    root = file.getroot()
    scaleSet = root.find("ScaleTool/ModelScaler/ScaleSet/objects")
    m = 0

    for element in scaleSet.iter():
        if element.tag == 'Scale':
            print(element.find("segment").text)
            if element.find("segment").text == "femur_r":
                femur_element = element
                m += 1
            elif element.find("segment").text == "tibia_r":
                tibia_element = element
                m += 1
        if m == 2:
            break
    
    if settings.scaling == "AB":
        ## Set Femur Distal Right Scales ##
        femur_scale = femur_element.find("scales").text
        scale_ffdr = ET.SubElement(scaleSet,"Scale")
        scales_ffdr = ET.SubElement(scale_ffdr,"scales")
        scales_ffdr.text = femur_scale
        segment_ffdr = ET.SubElement(scale_ffdr, "segment")
        segment_ffdr.text = "femur_distal_r"
        apply_ffdr = ET.SubElement(scale_ffdr, "apply")
        apply_ffdr.text = "true"

        ## Set Tibia Proximal Right Scales ##
        tibia_scale = tibia_element.find("scales").text
        scale_ttpr = ET.SubElement(scaleSet,"Scale")
        scales_ttpr = ET.SubElement(scale_ttpr,"scales")
        scales_ttpr.text = tibia_scale
        segment_ttpr = ET.SubElement(scale_ttpr, "segment")
        segment_ttpr.text = "tibia_proximal_r"
        apply_ttpr = ET.SubElement(scale_ttpr, "apply")
        apply_ttpr.text = "true"

        ## Set Patella Scales ##
        femur_scaleFloat = np.array([float(femur_scale.split(' ')[1]), float(femur_scale.split(' ')[2]), float(femur_scale.split(' ')[3])])
        patella_scaleFactors = femur_scaleFloat
        patella_scale = " ".join([str(patella_scaleFactors[0]),str(patella_scaleFactors[1]),str(patella_scaleFactors[2])])

        scale_ptr = ET.SubElement(scaleSet,"Scale")
        scales_ptr = ET.SubElement(scale_ptr,"scales")
        scales_ptr.text = patella_scale
        segment_ptr = ET.SubElement(scale_ptr, "segment")
        segment_ptr.text = "patella_r"
        apply_ptr = ET.SubElement(scale_ptr, "apply")
        apply_ptr.text = "true"

    elif settings.scaling == "LA": # Tibia & Femur scaled separately, long axis scale factors
        ## Set Femur Distal Right Scales ##
        femur_scale = femur_element.find("scales").text
        scale_ffdr = ET.SubElement(scaleSet,"Scale")
        scales_ffdr = ET.SubElement(scale_ffdr,"scales")
        femur_scaleFloat = float(femur_scale.split(' ')[2]) #Long Axis Only
        femur_scale_txt = " ".join([str(femur_scaleFloat),str(femur_scaleFloat),str(femur_scaleFloat)])
        scales_ffdr.text = femur_scale_txt
        segment_ffdr = ET.SubElement(scale_ffdr, "segment")
        segment_ffdr.text = "femur_distal_r"
        apply_ffdr = ET.SubElement(scale_ffdr, "apply")
        apply_ffdr.text = "true"

        ## Set Tibia Proximal Right Scales ##
        tibia_scale = tibia_element.find("scales").text
        scale_ttpr = ET.SubElement(scaleSet,"Scale")
        scales_ttpr = ET.SubElement(scale_ttpr,"scales")
        tibia_scaleFloat = float(tibia_scale.split(' ')[2])
        tibia_scale_txt = " ".join([str(tibia_scaleFloat),str(tibia_scaleFloat),str(tibia_scaleFloat)])
        scales_ttpr.text = tibia_scale_txt
        segment_ttpr = ET.SubElement(scale_ttpr, "segment")
        segment_ttpr.text = "tibia_proximal_r"
        apply_ttpr = ET.SubElement(scale_ttpr, "apply")
        apply_ttpr.text = "true"    

        ## Set Patella Scales ## 
        patella_scale_txt = femur_scale_txt
        patella_scaleFactors = np.array([femur_scaleFloat,femur_scaleFloat,femur_scaleFloat])
        scale_ptr = ET.SubElement(scaleSet,"Scale")
        scales_ptr = ET.SubElement(scale_ptr,"scales")
        scales_ptr.text = patella_scale_txt
        segment_ptr = ET.SubElement(scale_ptr, "segment")
        segment_ptr.text = "patella_r"
        apply_ptr = ET.SubElement(scale_ptr, "apply")
        apply_ptr.text = "true"

    elif settings.scaling == "WA": # Tibia & Femur Scaled Same, Weighted Average of Long Axis 
        # Calculate Weighted Average #
        femur_scale = femur_element.find("scales").text
        femur_scaleFloat = float(femur_scale.split(' ')[2]) #np.array([float(femur_scale.split(' ')[1]), float(femur_scale.split(' ')[2]), float(femur_scale.split(' ')[3])])

        tibia_scale = tibia_element.find("scales").text
        tibia_scaleFloat = float(tibia_scale.split(' ')[2]) # np.array([float(tibia_scale.split(' ')[1]), float(tibia_scale.split(' ')[2]), float(tibia_scale.split(' ')[3])])

        avg_scale = (femur_scaleFloat + tibia_scaleFloat) / 2
        avg_scale_txt = " ".join([str(avg_scale),str(avg_scale),str(avg_scale)])


        ## Set Femur Distal Right Scales ##
        scale_ffdr = ET.SubElement(scaleSet,"Scale")
        scales_ffdr = ET.SubElement(scale_ffdr,"scales")
        scales_ffdr.text = avg_scale_txt
        segment_ffdr = ET.SubElement(scale_ffdr, "segment")
        segment_ffdr.text = "femur_distal_r"
        apply_ffdr = ET.SubElement(scale_ffdr, "apply")
        apply_ffdr.text = "true"

        ## Set Tibia Proximal Right Scales ##
        scale_ttpr = ET.SubElement(scaleSet,"Scale")
        scales_ttpr = ET.SubElement(scale_ttpr,"scales")
        scales_ttpr.text = avg_scale_txt
        segment_ttpr = ET.SubElement(scale_ttpr, "segment")
        segment_ttpr.text = "tibia_proximal_r"
        apply_ttpr = ET.SubElement(scale_ttpr, "apply")
        apply_ttpr.text = "true"    

        ## Set Patella Scales ## 
        scale_ptr = ET.SubElement(scaleSet,"Scale")
        scales_ptr = ET.SubElement(scale_ptr,"scales")
        scales_ptr.text = avg_scale_txt
        patella_scaleFactors = np.array([avg_scale,avg_scale,avg_scale])
        segment_ptr = ET.SubElement(scale_ptr, "segment")
        segment_ptr.text = "patella_r"
        apply_ptr = ET.SubElement(scale_ptr, "apply")
        apply_ptr.text = "true"

    # Write xml with new scale factors
    file.write(path_scaling_mod)

    ## Replace Markerset before Scaling ##

    # Remove Marker Set
    file2 = ET.parse(path_comak_model)
    root2 = file2.getroot()
    model = root2.find("Model")
    model.remove(model.find("MarkerSet"))

    # Copy New Marker Set
    file3 = ET.parse(path_markers)
    root3 = file3.getroot()
    model3 = root3.find("Model/MarkerSet")
    type(model3)
    markers = copy.deepcopy(model3)

    # Add New Markers to File
    model.append(markers)

    # Scale Cartilage, Same Scale Factors as Associated Bodies
    contactMesh = root2.find("Model/ContactGeometrySet/objects")
    m = 0

    for element in contactMesh.iter():
        if element.tag == 'Smith2018ContactMesh':
            for subelement in element.iter():
                ## for changing scale factor socket ##
                if subelement.tag == 'socket_scale_frame':
                    print(element.get('name'))
                    if element.get('name') == 'femur_cartilage':
                        subelement.text = '/bodyset/femur_distal_r'
                        m = m+1
                        # print(subelement.text)
                    elif element.get('name') == 'tibia_cartilage':
                        subelement.text = '/bodyset/tibia_proximal_r'
                        m = m+1
                        # print(subelement.text)
                    elif element.get('name') == 'patella_cartilage':
                        subelement.text = '/bodyset/patella_r'
                        m = m+1
                        # print(subelement.text)
                ##
            if m == 3:
                break    
    file2.write(path_model_new_markers) 

    ligament = ['ITB1']

    model = osim.Model(path_model_new_markers)
    state = model.initSystem()
    ligaments = model.upd_ForceSet()
    bodyset = model.getBodySet()
        
    for idx2 in range(bodyset.getSize()):
        body = bodyset.get(idx2)
        name = body.getName()
        if name == 'tibia_proximal_r':
            print(name)
            break

    joint_name = 'tibia_tibia_proximal_r'
    joint = model.getJointSet().get(joint_name)
    translate = joint.get_frames(0).get_translation()

    print(translate)

    joint_name = 'pf_r'
    pf_joint = model.getJointSet().get(joint_name)
    for i in range(3,6): # [3,5]: 
        orig_value = pf_joint.get_coordinates(i).getDefaultValue()
        print(orig_value)
        pf_joint.get_coordinates(i).setDefaultValue(orig_value*patella_scaleFactors[i-3])
        print(pf_joint.get_coordinates(i).getDefaultValue())


    # Modifying the ligaments
    for i in range(0,(ligaments.getSize())):
        ligament = osim.Blankevoort1991Ligament.safeDownCast(ligaments.get(i))
        # ligament_upd = osim.Blankevoort1991Ligament.safeDownCast(ligaments_upd.get(i))
        if ligament is not None:
            if ligament.getName() == 'ITB1':
                pt_idx = 2
                # ligament.setSlackLengthFromReferenceStrain(slackLength[sL],state)
                geopath = ligament.get_GeometryPath()
                path_pointset = geopath.getPathPointSet()
                pt = path_pointset.get(pt_idx)
                orig_loc = [pt.getLocation(state)[x] for x in range(3)]
                pt_ = [pt.getLocation(state)[x] for x in range(3)]
                    # for idx, new_loc in zip(indices, locations):
                        # pt_[idx] = new_loc
                new_loc = np.array(orig_loc) + np.array([translate[0],translate[1],translate[2]])
                # print(new_loc)
                path_point_ = osim.PathPoint.safeDownCast(pt)
                # print('Parent Frame1:')
                # print(path_point_.getParentFrame().getName())
                path_point_.setParentFrame(body)
                # print('Parent Frame2:')
                # print(path_point_.getParentFrame().getName())
                path_point_.setLocation(osim.Vec3(*new_loc))
                updated_loc = [geopath.getPathPointSet().get(pt_idx).getLocation(state)[x] for x in range(3)]                    
                print(f'Orig location: {orig_loc}\nNew location: {updated_loc}')

    # joint_name = 'pf_r'
    # pf_joint = model.getJointSet().get(joint_name)
    # for i in [3,5]:#range(3,6):
    #     orig_value = pf_joint.get_coordinates(i).getDefaultValue()
    #     print(orig_value)
    #     pf_joint.get_coordinates(i).setDefaultValue(orig_value*patella_scaleFactors[i-3])
    #     print(pf_joint.get_coordinates(i).getDefaultValue())
  
    state = model.initSystem()
    model.printToXML(path_model_new_markers)







    ## Scale Model ##
    scaleTool = osim.ScaleTool(path_scaling_mod)

    genModel = scaleTool.getGenericModelMaker()
    modelScale = scaleTool.getModelScaler()
    markerScale = scaleTool.getMarkerPlacer()

    # Set Model file name (path within same folder as scaling file)
    genModel.setModelFileName(name_model_new_markers)

    # Set Output File Names
    modelScale.setOutputScaleFileName('scaledLenhart.xml')
    
    name_model_scaled = "scaledLenhart.osim"
    modelScale.setOutputModelFileName(name_model_scaled)

    scaleTool.run()

    ## Update Model Wrapping ##
    if settings.modelWrap == True:
        path_model = settings.model_dir + '/' + name_model_scaled
        model = osim.Model(path_model)

        ellipsoid = osim.WrapEllipsoid()
        ellipsoid.set_xyz_body_rotation(osim.Vec3([0, 0, -0.28]))
        ellipsoid.set_translation(osim.Vec3([-0.04, -0.383198, 0]))
        ellipsoid.set_quadrant('all')
        ellipsoid.set_dimensions(osim.Vec3([0.08, 0.035, 0.2]))
        ellipsoid.setName("KnExt_at_fem_r_2")

        body_add_ellipsoid = 'femur_r'

        bodyset = model.getBodySet()

        for idx in range(bodyset.getSize()):
            body = bodyset.get(idx)
            name = body.getName()
            if name == body_add_ellipsoid:
                print(name)
                body.addWrapObject(ellipsoid)
                print('Added wrap')

        def update_path_point(muscle, pt_idx, indices, locations):
            if type(indices) not in [list, tuple]:
                indices = [indices,]
            if type(locations) not in [list, tuple]:
                locations = [locations,]
            geopath = muscle.getGeometryPath()
            path_pointset = geopath.getPathPointSet()
            pt = path_pointset.get(pt_idx)
            orig_loc = [pt.getLocation(state)[x] for x in range(3)]
            pt_ = [pt.getLocation(state)[x] for x in range(3)]
            for idx, new_loc in zip(indices, locations):
                pt_[idx] = new_loc
            path_point_ = osim.PathPoint.safeDownCast(pt)
            # print('Parent Frame1:')
            # print(path_point_.getParentFrame().getName())
            # path_point_.setLocation(osim.Vec3(pt_))
            # updated_loc = [geopath.getPathPointSet().get(pt_idx).getLocation(state)[x] for x in range(3)]
            # print(f'Orig location: {orig_loc}\nNew location: {updated_loc}')

        quads = [
            'recfem_r',
            'vasint_r',
            'vaslat_r',
            'vasmed_r'
        ]

        muscles = model.getMuscles()
        n_muscles = muscles.getSize()

        state = model.initSystem()

        for muscle_idx in range(n_muscles):
            muscle = muscles.get(muscle_idx)
            name = muscle.getName()

            # ###Update muscle strength
            # force_old = muscle.get_max_isometric_force()
            # force_new = force_old * 1.5 ## scaling factor
            # muscle.set_max_isometric_force(force_new)

            if name in quads:
                # Update each quads muscle to wrap around new object. 
                geopath = muscle.getGeometryPath()
                wrapset = geopath.getWrapSet()
                wrap = wrapset.get(0)
                wrap.set_wrap_object(0, ellipsoid.getName())
            
            if name == 'recfem_r':
                print(muscle_idx, name)
                update_path_point(
                    muscle=muscle, 
                    pt_idx=1, 
                    indices=[0,], 
                    locations=[0.0,]
                )
            elif name == 'vasint_r':
                print(muscle_idx, name)
                update_path_point(
                    muscle=muscle, 
                    pt_idx=2, 
                    indices=[0, 1], 
                    locations=[0.0, 0.0156828]
                )
            elif name == 'vasmed_r':
                print(muscle_idx, name)
                update_path_point(muscle=muscle, pt_idx=2, indices=[0], locations=[0.0])

            model.printToXML(settings.model_file)

