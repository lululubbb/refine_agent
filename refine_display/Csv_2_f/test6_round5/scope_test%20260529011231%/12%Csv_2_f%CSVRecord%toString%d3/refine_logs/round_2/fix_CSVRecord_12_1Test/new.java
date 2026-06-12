package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_12_1Test {

    @Test
    public void testtoString_emptyArray() throws Exception {
        String[] values = new String[0];
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = record.toString();
        
        Assertions.assertEquals("[]", result);
    }

    @Test
    public void testtoString_singleElement() throws Exception {
        String[] values = {"value1"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = record.toString();
        
        Assertions.assertEquals("[value1]", result);
    }

    @Test
    public void testtoString_multipleElements() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = record.toString();
        
        Assertions.assertEquals("[value1, value2, value3]", result);
    }

    @Test
    public void testtoString_withNullValue() throws Exception {
        String[] values = {"value1", null, "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = record.toString();
        
        Assertions.assertEquals("[value1, null, value3]", result);
    }

    @Test
    public void testtoString_withEmptyString() throws Exception {
        String[] values = {"value1", "", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = record.toString();
        
        Assertions.assertEquals("[value1, , value3]", result);
    }

    @Test
    public void testtoString_withAllNulls() throws Exception {
        String[] values = {null, null, null};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = record.toString();
        
        Assertions.assertEquals("[null, null, null]", result);
    }

    @Test
    public void testtoString_withMixedValues() throws Exception {
        String[] values = {"value1", null, "", "value4"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = record.toString();
        
        Assertions.assertEquals("[value1, null, , value4]", result);
    }

    @Test
    public void testtoString_boundaryCase() throws Exception {
        String[] values = {null, "", "value3", "value4", "value5"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = record.toString();
        
        Assertions.assertEquals("[null, , value3, value4, value5]", result);
    }

    @Test
    public void testtoString_exceptionThrowingPath() throws Exception {
        String[] values = {null};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertThrows(NullPointerException.class, () -> {
            record.get(1); // Accessing out of bounds
        });
    }
}