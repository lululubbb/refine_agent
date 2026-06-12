package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_12_6Test {

    @Test
    public void testToString_emptyArray() throws Exception {
        CSVRecord record = new CSVRecord(new String[0], Collections.emptyMap(), null, 0);
        String result = record.toString();
        Assertions.assertEquals("[]", result);
    }

    @Test
    public void testToString_singleElementArray() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1"}, Collections.emptyMap(), null, 1);
        String result = record.toString();
        Assertions.assertEquals("[value1]", result);
    }

    @Test
    public void testToString_multipleElementsArray() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2", "value3"}, Collections.emptyMap(), null, 2);
        String result = record.toString();
        Assertions.assertEquals("[value1, value2, value3]", result);
    }

    @Test
    public void testToString_nullElementsArray() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1", null, "value3"}, Collections.emptyMap(), null, 3);
        String result = record.toString();
        Assertions.assertEquals("[value1, null, value3]", result);
    }

    @Test
    public void testToString_withMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        mapping.put("key2", 1);
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 4);
        String result = record.toString();
        Assertions.assertEquals("[value1, value2]", result);
    }

    @Test
    public void testToString_withEmptyMapping() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, Collections.emptyMap(), null, 5);
        String result = record.toString();
        Assertions.assertEquals("[value1, value2]", result);
    }

    @Test
    public void testToString_withLeadingNull() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{null, "value2"}, Collections.emptyMap(), null, 6);
        String result = record.toString();
        Assertions.assertEquals("[null, value2]", result);
    }

    @Test
    public void testToString_withTrailingNull() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1", null}, Collections.emptyMap(), null, 7);
        String result = record.toString();
        Assertions.assertEquals("[value1, null]", result);
    }

    @Test
    public void testToString_boundaryValues() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{}, Collections.emptyMap(), null, Long.MAX_VALUE);
        String result = record.toString();
        Assertions.assertEquals("[]", result);
        
        record = new CSVRecord(new String[]{null}, Collections.emptyMap(), null, Long.MAX_VALUE);
        result = record.toString();
        Assertions.assertEquals("[null]", result);
        
        record = new CSVRecord(new String[]{"value1", "value2", "value3"}, Collections.emptyMap(), null, Long.MAX_VALUE);
        result = record.toString();
        Assertions.assertEquals("[value1, value2, value3]", result);
    }
}