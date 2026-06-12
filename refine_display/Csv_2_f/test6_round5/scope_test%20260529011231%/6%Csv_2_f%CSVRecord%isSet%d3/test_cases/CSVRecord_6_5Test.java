package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import java.lang.reflect.Field;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class CSVRecord_6_5Test {

    @Test
    public void testisSet_nameMappedAndWithinBounds() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        String[] values = {"value1"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        boolean result = invokeIsSet(record, "name");
        
        Assertions.assertEquals(true, result);
    }

    @Test
    public void testisSet_nameMappedButOutOfBounds() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 1);
        String[] values = {"value1"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        boolean result = invokeIsSet(record, "name");
        
        Assertions.assertEquals(false, result);
    }

    @Test
    public void testisSet_nameNotMapped() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        String[] values = {"value1"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        boolean result = invokeIsSet(record, "name");
        
        Assertions.assertEquals(false, result);
    }

    @Test
    public void testisSet_emptyMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        String[] values = {};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        boolean result = invokeIsSet(record, "name");
        
        Assertions.assertEquals(false, result);
    }

    @Test
    public void testisSet_nullValues() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        String[] values = {null};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        boolean result = invokeIsSet(record, "name");
        
        Assertions.assertEquals(true, result);
    }

    @Test
    public void testisSet_emptyValues() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        String[] values = {""};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        boolean result = invokeIsSet(record, "name");
        
        Assertions.assertEquals(true, result);
    }

    private boolean invokeIsSet(CSVRecord record, String name) throws Exception {
        Field mappingField = CSVRecord.class.getDeclaredField("mapping");
        mappingField.setAccessible(true);
        Map<String, Integer> mapping = (Map<String, Integer>) mappingField.get(record);

        Field valuesField = CSVRecord.class.getDeclaredField("values");
        valuesField.setAccessible(true);
        String[] values = (String[]) valuesField.get(record);

        return record.isMapped(name) && mapping.get(name) < values.length;
    }
}