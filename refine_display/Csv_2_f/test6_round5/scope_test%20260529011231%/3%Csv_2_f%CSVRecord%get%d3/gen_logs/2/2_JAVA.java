package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_3_2Test {

    @Test
    public void testGet_normalCase() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 0);
        mapping.put("header2", 1);
        mapping.put("header3", 2);
        
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        String result = record.get("header1");
        Assertions.assertEquals("value1", result);
    }

    @Test
    public void testGet_keyNotFound() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        String result = record.get("headerNotFound");
        Assertions.assertNull(result);
    }

    @Test
    public void testGet_noMapping() {
        String[] values = {"value1", "value2"};
        
        CSVRecord record = new CSVRecord(values, null, null, 1);
        Assertions.assertThrows(IllegalStateException.class, () -> record.get("header1"));
    }

    @Test
    public void testGet_indexOutOfBounds() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 2); // Invalid index

        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        Assertions.assertThrows(IllegalArgumentException.class, () -> record.get("header1"));
    }

    @Test
    public void testGet_emptyValues() throws Exception {
        String[] values = {};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 0);

        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        Assertions.assertThrows(IllegalArgumentException.class, () -> record.get("header1"));
    }
}