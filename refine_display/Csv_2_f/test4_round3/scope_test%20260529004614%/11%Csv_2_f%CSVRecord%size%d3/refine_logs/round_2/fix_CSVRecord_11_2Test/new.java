package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_11_2Test {

    @Test
    public void testSize_emptyArray() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{});
        Assertions.assertEquals(0, record.size());
    }

    @Test
    public void testSize_singleElementArray() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{"value1"});
        Assertions.assertEquals(1, record.size());
        Assertions.assertEquals("value1", record.get(0));
    }

    @Test
    public void testSize_multipleElementsArray() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{"value1", "value2", "value3"});
        Assertions.assertEquals(3, record.size());
        Assertions.assertEquals("value1", record.get(0));
        Assertions.assertEquals("value2", record.get(1));
        Assertions.assertEquals("value3", record.get(2));
    }

    @Test
    public void testSize_boundaryValues() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{"", "value2", " "});
        Assertions.assertEquals(3, record.size());
        Assertions.assertEquals("", record.get(0));
        Assertions.assertEquals("value2", record.get(1));
        Assertions.assertEquals(" ", record.get(2));
    }

    @Test
    public void testSize_withNullValues() throws Exception {
        CSVRecord record = createCSVRecord(new String[]{null, "value2", null});
        Assertions.assertEquals(3, record.size());
        Assertions.assertEquals(null, record.get(0));
        Assertions.assertEquals("value2", record.get(1));
        Assertions.assertEquals(null, record.get(2));
    }

    private CSVRecord createCSVRecord(String[] values) throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance(values, mapping, null, 0);
    }
}