package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_12_5Test {

    @Test
    public void testToString_normalCase() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        mapping.put("key2", 1);
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = invokeToString(record);
        
        Assertions.assertEquals("[value1, value2, value3]", result);
    }

    @Test
    public void testToString_emptyArray() throws Exception {
        String[] values = {};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = invokeToString(record);
        
        Assertions.assertEquals("[]", result);
    }

    @Test
    public void testToString_singleElement() throws Exception {
        String[] values = {"singleValue"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = invokeToString(record);
        
        Assertions.assertEquals("[singleValue]", result);
    }

    @Test
    public void testToString_multipleSpaces() throws Exception {
        String[] values = {"   ", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        mapping.put("key2", 1);
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = invokeToString(record);
        
        Assertions.assertEquals("[   , value2, value3]", result);
    }

    @Test
    public void testToString_specialCharacters() throws Exception {
        String[] values = {"value1", "value@2", "value#3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        mapping.put("key2", 1);
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = invokeToString(record);
        
        Assertions.assertEquals("[value1, value@2, value#3]", result);
    }

    @Test
    public void testToString_boundaryValues() throws Exception {
        String[] values = {null, "", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        mapping.put("key2", 1);
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = invokeToString(record);
        
        Assertions.assertEquals("[null, , value3]", result);
    }

    @Test
    public void testToString_largeInput() throws Exception {
        String[] values = new String[1000];
        Arrays.fill(values, "value");
        Map<String, Integer> mapping = new HashMap<>();
        for (int i = 0; i < values.length; i++) {
            mapping.put("key" + (i + 1), i);
        }
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = invokeToString(record);
        
        Assertions.assertTrue(result.startsWith("[value") && result.endsWith("]"));
        Assertions.assertTrue(result.contains(", value"));
        Assertions.assertFalse(result.contains(", ..., value")); // Corrected assertion
    }

    private String invokeToString(CSVRecord record) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("toString");
        method.setAccessible(true);
        return (String) method.invoke(record);
    }
}