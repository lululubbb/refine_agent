package org.apache.commons.csv;

import java.util.Arrays;
import java.util.Iterator;
import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;
import java.lang.reflect.Method;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class CSVRecord_5_2Test {

    @Test
    public void testIsMapped_mappingIsNull() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1"}, null, null, 1);
        boolean result = invokeIsMapped(record, "name");
        Assertions.assertEquals(false, result, "Expected mapping to be null, thus isMapped should return false.");
    }

    @Test
    public void testIsMapped_mappingDoesNotContainKey() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("otherName", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        boolean result = invokeIsMapped(record, "name");
        Assertions.assertEquals(false, result, "Expected mapping to not contain 'name', thus isMapped should return false.");
    }

    @Test
    public void testIsMapped_mappingContainsKey() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        boolean result = invokeIsMapped(record, "name");
        Assertions.assertEquals(true, result, "Expected mapping to contain 'name', thus isMapped should return true.");
    }

    private boolean invokeIsMapped(CSVRecord record, String name) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("isMapped", String.class);
        method.setAccessible(true);
        return (boolean) method.invoke(record, name);
    }
}